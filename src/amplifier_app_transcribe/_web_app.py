"""
Streamlit Web Interface

Browser-based UI for single-video transcription with settings.
Design: Clean minimalism showcasing craft while delivering utility.
"""

import os
import time
from pathlib import Path

import streamlit as st

# Page config
st.set_page_config(
    page_title="Amplifier Transcribe",
    page_icon="🎯",
    layout="wide",
)

# Custom CSS - Focus on what actually works in Streamlit
st.markdown(
    """
    <style>
    /* Reduce padding where Streamlit allows */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Hero Section */
    .hero-title {
        font-size: 3rem;
        font-weight: 600;
        color: #1A202C;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }

    .hero-subtitle {
        font-size: 1.25rem;
        color: #4A5568;
        margin-bottom: 2rem;
        line-height: 1.6;
    }

    /* Feature Cards */
    .feature-card {
        background: #F8FAFC;
        border-radius: 8px;
        padding: 1.5rem;
        border-left: 4px solid #2E5BFF;
        margin-bottom: 1rem;
    }

    .feature-title {
        font-weight: 600;
        color: #2D3748;
        margin-bottom: 0.5rem;
    }

    .feature-text {
        color: #4A5568;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* Input Fields - Better visibility */
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 2px solid #CBD5E0 !important;
        transition: all 0.2s ease;
        font-size: 1rem;
    }

    .stTextInput > div > div > input:focus {
        border-color: #2E5BFF !important;
        box-shadow: 0 0 0 3px rgba(46, 91, 255, 0.1) !important;
    }

    /* Checkbox */
    .stCheckbox {
        padding-top: 0.75rem;
    }

    /* Center button container */
    div[data-testid="column"]:has(> div > div > div > button[kind="primary"]) {
        display: flex;
        justify-content: center;
    }

    /* Results Container */
    .results-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 2rem;
        margin-top: 2rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    /* Success banner */
    .success-banner {
        background: linear-gradient(135deg, #10B981 0%, #34D399 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-weight: 500;
    }

    /* Code */
    code {
        background: #F1F5F9;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
        font-size: 0.9em;
        color: #1A202C;
    }

    /* Divider */
    hr {
        margin: 2rem 0;
        border-color: #E2E8F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
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

# Hero Section
st.markdown('<h1 class="hero-title">Transcribe</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-subtitle">Transform video and audio into searchable transcripts with AI-powered insights</p>',
    unsafe_allow_html=True,
)

# Feature Overview (collapsed by default for clean initial view)
with st.expander("💡 How it works", expanded=False):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">1. Process Audio</div>
                <div class="feature-text">Downloads from YouTube or accepts local files</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">2. Transcribe</div>
                <div class="feature-text">Uses OpenAI Whisper for accurate speech-to-text</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">3. Analyze</div>
                <div class="feature-text">Extracts key insights and memorable quotes</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">4. Format</div>
                <div class="feature-text">Creates timestamped, searchable documents</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# Settings Section
with st.expander("⚙️ Configuration", expanded=False):
    st.markdown("**API Keys** — Required for transcription and insights")

    # OpenAI API Key
    openai_key_set = bool(os.getenv("OPENAI_API_KEY"))
    if openai_key_set:
        st.success("✓ OpenAI configured")
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
            st.success("✓ Configured for this session")

    # Anthropic API Key
    anthropic_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))
    if anthropic_key_set:
        st.success("✓ Anthropic configured")
    else:
        anthropic_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Optional — enables AI-powered insights",
            disabled=st.session_state.processing,
            key="anthropic_key_input",
        )
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
            st.success("✓ Configured for this session")

    st.divider()

    st.markdown("**Output Directory**")
    output_dir = st.text_input(
        "Save location",
        value="~/transcripts",
        help="Where transcripts will be saved",
        disabled=st.session_state.processing,
        key="output_dir_input",
    )

# Check API keys before allowing transcription
if not os.getenv("OPENAI_API_KEY"):
    st.warning("⚠️ Configure OpenAI API key above to begin")
    st.stop()

st.markdown("### Start Transcription")

# Input section with better layout
col1, col2 = st.columns([5, 1])

with col1:
    url = st.text_input(
        "YouTube URL or audio file path",
        placeholder="https://youtube.com/watch?v=... or /path/to/audio.mp3",
        disabled=st.session_state.processing,
        label_visibility="collapsed",
        key="url_input",
    )

with col2:
    enhance = st.checkbox(
        "AI Insights",
        value=True,
        disabled=st.session_state.processing,
        key="enhance_checkbox",
        help="Generate summaries and extract key quotes",
    )

# Process button - left aligned
transcribe_button = st.button(
    "Transcribe",
    disabled=st.session_state.processing or not url,
    type="primary",
)

if transcribe_button:
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
    st.markdown('<div class="success-banner">✅ Transcription complete</div>', unsafe_allow_html=True)
    st.info(f"📁 Saved to: `{st.session_state.results['output_dir']}`")

    st.markdown('<div class="results-container">', unsafe_allow_html=True)

    # Tabbed interface
    if st.session_state.results["insights"]:
        tab1, tab2 = st.tabs(["📊 Insights", "📝 Transcript"])

        with tab1:
            st.markdown(st.session_state.results["insights"])

        with tab2:
            st.markdown(st.session_state.results["transcript"])
    else:
        st.markdown("### 📝 Transcript")
        st.markdown(st.session_state.results["transcript"])

    st.markdown("</div>", unsafe_allow_html=True)

    # Reset button
    if st.button("Process Another"):
        st.session_state.results = None
        st.session_state.error = None
        st.rerun()
