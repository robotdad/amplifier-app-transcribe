"""
Storage Core Implementation

Saves transcripts in multiple formats to organized directories.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from .formatter import format_transcript
from .insights import generate_insights

logger = logging.getLogger(__name__)


class TranscriptStorage:
    """Save transcripts in multiple formats."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize storage.

        Args:
            output_dir: Base output directory (default: ~/transcripts)
        """
        if output_dir:
            self.output_dir = Path(output_dir).expanduser()
        else:
            self.output_dir = Path("~/transcripts").expanduser()

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        transcript,
        video_info,
        audio_path: Path | None = None,
        save_json: bool = True,
        save_markdown: bool = True,
        save_vtt: bool = True,
        save_srt: bool = True,
    ) -> Path:
        """Save transcript in multiple formats.

        Args:
            transcript: Transcript object
            video_info: Video information
            audio_path: Path to audio file to save (optional)
            save_json: Save as JSON
            save_markdown: Save as Markdown
            save_vtt: Save as WebVTT
            save_srt: Save as SRT

        Returns:
            Path to output directory containing all files
        """
        # Create output directory for this video
        video_id = self._sanitize_filename(video_info.id)
        video_dir = self.output_dir / video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving to: {video_dir}")

        # Save audio file if provided
        saved_audio_path = None
        if audio_path and audio_path.exists():
            saved_audio_path = self.save_audio(audio_path, video_dir)

        # Save in requested formats
        saved_files = []

        if save_json:
            json_path = self._save_json(transcript, video_info, video_dir, saved_audio_path)
            saved_files.append(f"JSON: {json_path.name}")

        if save_markdown:
            md_path = self._save_markdown(transcript, video_info, video_dir)
            saved_files.append(f"MD: {md_path.name}")

        if save_vtt and transcript.segments:
            vtt_path = self._save_vtt(transcript, video_dir)
            saved_files.append(f"VTT: {vtt_path.name}")

        if save_srt and transcript.segments:
            srt_path = self._save_srt(transcript, video_dir)
            saved_files.append(f"SRT: {srt_path.name}")

        logger.info(f"Saved {len(saved_files)} files: {', '.join(saved_files)}")
        return video_dir

    def save_audio(self, audio_path: Path, output_dir: Path) -> Path:
        """Save audio file to output directory.

        Args:
            audio_path: Source audio file path
            output_dir: Target directory

        Returns:
            Path to saved audio file
        """
        import shutil

        target_path = output_dir / "audio.mp3"

        # Don't copy if already in place
        if audio_path.absolute() == target_path.absolute():
            return target_path

        # Copy audio file
        shutil.copy2(audio_path, target_path)
        logger.info(f"Saved audio to: {target_path}")

        return target_path

    def save_insights(
        self,
        summary,
        quotes: list | None,
        title: str,
        output_dir: Path,
    ) -> Path:
        """Save combined insights document with summary and quotes.

        Args:
            summary: Summary object with overview, key_points, and themes
            quotes: List of Quote objects
            title: Title of the content
            output_dir: Directory to save the insights

        Returns:
            Path to saved insights file
        """
        # Generate insights document
        insights_content = generate_insights(
            summary=summary,
            quotes=quotes,
            title=title,
        )

        # Save to file
        insights_path = output_dir / "insights.md"
        with open(insights_path, "w", encoding="utf-8") as f:
            f.write(insights_content)

        logger.info(f"Saved insights to: {insights_path}")
        return insights_path

    def has_transcript(self, video_id: str) -> bool:
        """Check if transcript already exists for a video.

        Args:
            video_id: Video identifier

        Returns:
            True if transcript.json exists
        """
        video_id_sanitized = self._sanitize_filename(video_id)
        transcript_path = self.output_dir / video_id_sanitized / "transcript.json"
        return transcript_path.exists()

    def load_transcript(self, video_id: str):
        """Load existing transcript from disk.

        Args:
            video_id: Video identifier

        Returns:
            Transcript object loaded from JSON, or None if not found
        """
        video_id_sanitized = self._sanitize_filename(video_id)
        transcript_path = self.output_dir / video_id_sanitized / "transcript.json"

        if not transcript_path.exists():
            return None

        try:
            with open(transcript_path, encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct transcript object from JSON
            # Create simple namespace object with transcript data
            from types import SimpleNamespace

            segments = [SimpleNamespace(**seg) for seg in data["transcript"]["segments"]]
            transcript = SimpleNamespace(
                text=data["transcript"]["text"],
                language=data["transcript"]["language"],
                duration=data["transcript"]["duration"],
                segments=segments,
            )

            logger.info(f"Loaded cached transcript from: {transcript_path}")
            return transcript

        except Exception as e:
            logger.warning(f"Failed to load cached transcript: {e}")
            return None

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        # Limit length
        return name[:100]

    def _save_json(
        self,
        transcript,
        video_info,
        output_dir: Path,
        audio_path: Path | None = None,
    ) -> Path:
        """Save transcript as JSON with metadata."""
        json_path = output_dir / "transcript.json"

        # Add audio metadata if audio file exists
        audio_metadata = None
        if audio_path and audio_path.exists():
            audio_metadata = {
                "filename": audio_path.name,
                "size_mb": round(audio_path.stat().st_size / (1024 * 1024), 2),
                "format": "mp3",
            }

        data = {
            "video": {
                "source": video_info.source,
                "title": video_info.title,
                "id": video_info.id,
                "duration": video_info.duration,
                "uploader": video_info.uploader,
                "description": video_info.description,
            },
            "transcript": {
                "text": transcript.text,
                "language": transcript.language,
                "duration": transcript.duration,
                "segments": [
                    {
                        "id": seg.id,
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                    }
                    for seg in transcript.segments
                ],
            },
            "audio": audio_metadata,
            "metadata": {
                "transcribed_at": datetime.now().isoformat(),
                "version": "1.0",
            },
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return json_path

    def _save_markdown(self, transcript, video_info, output_dir: Path) -> Path:
        """Save transcript as readable Markdown."""
        md_path = output_dir / "transcript.md"

        # Format transcript with paragraphs and timestamps
        formatted_content = format_transcript(
            transcript=transcript,
            video_info=video_info,
            video_url=video_info.source if "youtube" in video_info.source.lower() else None,
        )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)

        return md_path

    def _save_vtt(self, transcript, output_dir: Path) -> Path:
        """Save transcript as WebVTT."""
        vtt_path = output_dir / "transcript.vtt"

        lines = ["WEBVTT", ""]

        for seg in transcript.segments:
            start = self._seconds_to_vtt(seg.start)
            end = self._seconds_to_vtt(seg.end)
            lines.append(f"{start} --> {end}")
            lines.append(seg.text.strip())
            lines.append("")

        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return vtt_path

    def _save_srt(self, transcript, output_dir: Path) -> Path:
        """Save transcript as SRT."""
        srt_path = output_dir / "transcript.srt"

        lines = []

        for i, seg in enumerate(transcript.segments, 1):
            start = self._seconds_to_srt(seg.start)
            end = self._seconds_to_srt(seg.end)
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(seg.text.strip())
            lines.append("")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return srt_path

    def _seconds_to_vtt(self, seconds: float) -> str:
        """Convert seconds to WebVTT timestamp (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def _seconds_to_srt(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
