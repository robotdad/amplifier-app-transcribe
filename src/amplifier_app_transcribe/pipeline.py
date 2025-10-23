"""
Transcription Pipeline - Main Orchestrator

Coordinates video transcription with state management for resume capability.
Uses WhisperTranscriber and VideoLoader from tool modules.
"""

# pyright: reportAttributeAccessIssue=false, reportMissingImports=false

import logging
from collections.abc import Callable

from amplifier_module_tool_whisper import WhisperTranscriber  # type: ignore
from amplifier_module_tool_youtube_dl import AudioExtractor, VideoLoader  # type: ignore

from .insights import QuoteExtractor, SummaryGenerator
from .state import StateManager, VideoProcessingResult
from .storage import TranscriptStorage

logger = logging.getLogger(__name__)

# Type alias for progress callback
ProgressCallback = Callable[[str, dict], None]


class TranscriptionPipeline:
    """Orchestrates the transcription pipeline using tool core classes."""

    def __init__(
        self,
        state_manager: StateManager | None = None,
        enhance: bool = True,
        force_download: bool = False,
        on_progress: ProgressCallback | None = None,
    ):
        """Initialize pipeline.

        Args:
            state_manager: State manager for persistence (creates new if None)
            enhance: Whether to enable AI enhancements (summaries/quotes)
            force_download: If True, skip cache and re-download audio
            on_progress: Optional callback for progress updates (stage, data) -> None
        """
        # Initialize tool core classes directly
        self.whisper = WhisperTranscriber()
        self.youtube = VideoLoader()
        self.audio_extractor = AudioExtractor()
        self.state = state_manager or StateManager()
        self.enhance = enhance
        self.force_download = force_download
        self.on_progress = on_progress

        # Initialize storage
        self.storage = TranscriptStorage()

        # Initialize AI enhancement components if enabled
        self.summary_generator = None
        self.quote_extractor = None
        if enhance:
            try:
                self.summary_generator = SummaryGenerator()
                self.quote_extractor = QuoteExtractor()
                logger.info("AI enhancement enabled (summaries and quotes)")
            except (ImportError, ValueError) as e:
                logger.warning(f"AI enhancement disabled: {e}")
                self.enhance = False

    def _report_progress(self, stage: str, data: dict | None = None) -> None:
        """Report progress to callback if registered.

        Args:
            stage: Pipeline stage name
            data: Optional metadata (cost, duration, video_id, etc.)
        """
        if self.on_progress:
            try:
                self.on_progress(stage, data or {})
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def process_video(self, source: str) -> bool:
        """Process a single video/audio source.

        Args:
            source: URL or file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Stage 1: Load video info
            self.state.update_stage("loading", source)
            self._report_progress("loading", {"source": source})

            # Determine if source is URL or local file
            is_url = source.startswith("http://") or source.startswith("https://")

            if is_url:
                # Get video metadata
                video_info = self.youtube.load(source)
            else:
                # Local file - create VideoInfo
                from pathlib import Path

                local_path = Path(source)
                video_info = type(
                    "VideoInfo",
                    (),
                    {
                        "id": local_path.stem,
                        "title": local_path.name,
                        "source": str(local_path),
                        "duration": 0.0,  # Will be determined during transcription
                        "uploader": "Local File",
                        "description": None,
                        "type": "file",
                    },
                )()

            # Check if already processed
            if self.state.is_already_processed(video_info.id):
                logger.info(f"⏭ Skipping (already processed): {video_info.title}")
                return True

            logger.info(f"Processing: {video_info.title}")
            if video_info.duration > 0:
                logger.info(f"  Duration: {video_info.duration / 60:.1f} minutes")

            # Estimate cost
            if hasattr(self.whisper, "estimate_cost"):
                cost = self.whisper.estimate_cost(video_info.duration)
                logger.info(f"  Estimated cost: ${cost:.3f}")
            else:
                cost = 0.0

            # Determine output directory for this video
            video_id = self.storage._sanitize_filename(video_info.id)
            output_dir = self.storage.output_dir / video_id
            output_dir.mkdir(parents=True, exist_ok=True)

            # Stage 2: Download/extract audio
            self.state.update_stage("extracting", video_info.id)
            self._report_progress("extracting", {"video_id": video_info.id, "title": video_info.title})

            if is_url:
                # Download audio using youtube tool
                audio_path = self.youtube.download_audio(
                    source, output_dir, output_filename="audio.mp3", use_cache=(not self.force_download)
                )
            else:
                # Local file - just use it directly or copy
                audio_path = Path(source)
                if not audio_path.exists():
                    raise FileNotFoundError(f"Audio file not found: {source}")

            # Stage 3: Compress if needed
            audio_path = self.audio_extractor.compress_for_api(audio_path)

            # Stage 4: Transcribe
            self.state.update_stage("transcribing", video_info.id)
            self._report_progress("transcribing", {"video_id": video_info.id, "duration": video_info.duration})
            transcript = self.whisper.transcribe(audio_path, prompt=f"Transcription of: {video_info.title}")

            # Stage 5: Save outputs
            self.state.update_stage("saving", video_info.id)
            self._report_progress("saving", {"video_id": video_info.id})
            output_dir = self.storage.save(transcript, video_info, audio_path)

            # Stage 6: AI Enhancement (if enabled)
            if self.enhance and self.summary_generator and self.quote_extractor:
                try:
                    self.state.update_stage("enhancing", video_info.id)
                    self._report_progress("enhancing", {"video_id": video_info.id})
                    logger.info("Generating AI enhancements...")

                    # Generate summary
                    summary = self.summary_generator.generate(transcript.text, video_info.title)

                    # Extract quotes
                    video_url = source if is_url else None
                    quotes = self.quote_extractor.extract(transcript, video_url, video_info.id)

                    # Save combined insights document
                    self.storage.save_insights(
                        summary=summary,
                        quotes=quotes,
                        title=video_info.title,
                        output_dir=output_dir,
                    )

                    logger.info("✓ AI enhancements complete")
                except Exception as e:
                    logger.warning(f"AI enhancement failed (transcript saved): {e}")

            # Record success
            result = VideoProcessingResult(
                video_id=video_info.id,
                source=source,
                status="success",
                output_dir=str(output_dir),
                duration_seconds=video_info.duration,
                cost_estimate=cost,
            )
            self.state.add_processed(result)

            return True

        except Exception as e:
            logger.error(f"Failed to process {source}: {e}")

            # Record failure
            result = VideoProcessingResult(
                video_id=source,
                source=source,
                status="failed",
                error=str(e),
            )
            self.state.add_failed(result)

            return False

    def run(self, sources: list[str], resume: bool = False) -> bool:
        """Run the transcription pipeline.

        Args:
            sources: List of video sources (URLs or files)
            resume: Whether to resume from saved state

        Returns:
            True if all videos processed successfully
        """
        # Store sources in state
        if not resume or not self.state.state.sources:
            self.state.state.sources = sources
            self.state.state.total_videos = len(sources)
            self.state.state.output_dir = str(self.storage.output_dir)
            self.state.save()

        # Get pending sources
        if resume:
            pending = self.state.get_pending_sources()
            if not pending:
                logger.info("No pending videos to process")
                self.state.mark_complete()
                return True
            logger.info(f"Resuming with {len(pending)} pending videos")
            sources_to_process = pending
        else:
            sources_to_process = sources

        logger.info(f"Processing {len(sources_to_process)} videos")
        logger.info(f"Output directory: {self.storage.output_dir}")

        # Process each video
        all_success = True
        for i, source in enumerate(sources_to_process, 1):
            logger.info(f"\n[{i}/{len(sources_to_process)}] {source}")

            if not self.process_video(source):
                all_success = False

            # Save state after each video
            self.state.save()

        # Mark complete
        self.state.mark_complete()
        self._report_progress("complete", {"total_processed": len(self.state.state.processed_videos)})

        return all_success
