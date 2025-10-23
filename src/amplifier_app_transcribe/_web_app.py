"""
Streamlit Web Interface

Browser-based UI for single-video transcription with settings.
"""

import os
import time
from pathlib import Path

import streamlit as st

# Page config
st.set_page_config(
    page_title="Transcribe",
    page_icon="🎥",
    layout="wide",
)

# Initialize session state
if "processing" not in st.session_state:
    st.session_state.processing = False
if "results" not in st.session_state:
    st.session_state.results = None
if "error" not in st.session_state:
    st.session_state.error = None
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "current_stage" not in st.session_state:
    st.session_state.current_stage = None

# Welcome screen
st.title("🎥 Transcribe")
st.info("""
**Transform YouTube videos and audio files into searchable transcripts**

This tool:
1. Downloads audio from YouTube or processes local files
2. Transcribes using OpenAI's Whisper API
3. Generates AI-powered insights and key quotes
4. Formats into readable, timestamped transcripts
""")

# Settings Expander (collapsed by default)
with st.expander("⚙️ Settings & Configuration", expanded=False):
    st.markdown("**API Keys** (Session-only, not saved to disk)")

    # OpenAI API Key
    openai_key_set = bool(os.getenv("OPENAI_API_KEY"))
    if openai_key_set:
        st.success("✓ OpenAI key set")
    else:
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Required for Whisper transcription",
            disabled=st.session_state.processing,
            key="openai_key_input",
        )
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
            st.success("✓ Key configured for this session")

    # Anthropic API Key
    anthropic_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))
    if anthropic_key_set:
        st.success("✓ Anthropic key set")
    else:
        anthropic_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Optional - for AI insights (summaries/quotes)",
            disabled=st.session_state.processing,
            key="anthropic_key_input",
        )
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
            st.success("✓ Key configured for this session")

    st.divider()

    st.markdown("**Output Directory**")
    output_dir = st.text_input(
        "Transcript save location",
        value="~/transcripts",
        help="Where transcripts will be saved",
        disabled=st.session_state.processing,
        key="output_dir_input",
    )

# Check API keys before allowing transcription
if not os.getenv("OPENAI_API_KEY"):
    st.warning("⚠️ Configure OpenAI API key in settings above to begin")
    st.stop()

# Input section
col1, col2 = st.columns([4, 1])

with col1:
    url = st.text_input(
        "YouTube URL or file path",
        placeholder="https://youtube.com/watch?v=... or /path/to/audio.mp3",
        disabled=st.session_state.processing,
        key="url_input",
    )

with col2:
    enhance = st.checkbox("AI Insights", value=True, disabled=st.session_state.processing, key="enhance_checkbox")

# Process button
if st.button("Transcribe", disabled=st.session_state.processing or not url, type="primary"):
    st.session_state.processing = True
    st.session_state.results = None
    st.session_state.error = None
    st.session_state.start_time = time.time()
    st.session_state.current_stage = "initializing"

    # Progress display
    progress_placeholder = st.empty()

    try:
        from amplifier_app_transcribe.pipeline import TranscriptionPipeline
        from amplifier_app_transcribe.state import StateManager

        # Progress callback
        def update_progress(stage: str, data: dict):
            st.session_state.current_stage = stage

        # Create pipeline
        pipeline = TranscriptionPipeline(
            state_manager=StateManager(),
            enhance=enhance,
            on_progress=update_progress,
        )

        # Override output directory from settings if configured
        if output_dir and output_dir != "~/transcripts":
            pipeline.storage.output_dir = Path(output_dir).expanduser()
            pipeline.storage.output_dir.mkdir(parents=True, exist_ok=True)

        # Show progress with spinner
        with progress_placeholder.container():
            with st.spinner("Processing..."):
                # Status display
                status_col1, status_col2 = st.columns(2)

                # Run pipeline (blocks)
                success = pipeline.process_video(url)

                # Update elapsed time periodically
                elapsed = time.time() - st.session_state.start_time
                status_col1.text(f"⏱️ {elapsed:.1f}s elapsed")
                status_col2.text(f"Stage: {st.session_state.current_stage}")

        if success:
            # Load results from disk
            video_id = pipeline.storage._sanitize_filename(pipeline.state.state.processed_videos[-1].video_id)
            output_dir_path = pipeline.storage.output_dir / video_id

            # Read files
            transcript_file = output_dir_path / "transcript.md"
            insights_file = output_dir_path / "insights.md"

            results = {
                "transcript": transcript_file.read_text() if transcript_file.exists() else "Transcript not found",
                "insights": insights_file.read_text() if insights_file.exists() and enhance else None,
                "output_dir": str(output_dir_path),
            }

            st.session_state.results = results
            progress_placeholder.empty()
        else:
            st.session_state.error = "Processing failed. Check logs for details."

    except Exception as e:
        st.session_state.error = str(e)

    finally:
        st.session_state.processing = False
        st.rerun()

# Error display
if st.session_state.error:
    st.error(f"❌ {st.session_state.error}")
    if st.button("Try Again"):
        st.session_state.error = None
        st.rerun()

# Results display
if st.session_state.results:
    st.success("✅ Transcription complete!")
    st.info(f"📁 Saved to: `{st.session_state.results['output_dir']}`")

    # Tabbed interface
    if st.session_state.results["insights"]:
        tab1, tab2 = st.tabs(["📊 Insights", "📝 Transcript"])

        with tab1:
            st.markdown(st.session_state.results["insights"])

        with tab2:
            st.markdown(st.session_state.results["transcript"])
    else:
        st.markdown("## 📝 Transcript")
        st.markdown(st.session_state.results["transcript"])

    # Reset button
    if st.button("Process Another"):
        st.session_state.results = None
        st.session_state.error = None
        st.rerun()
