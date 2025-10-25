"""
Web UI Launcher

Spawns Streamlit server for browser-based interface.
"""

import os
import subprocess
import sys
from pathlib import Path


def _setup_streamlit_config() -> None:
    """Create Streamlit credentials file to skip email prompt."""
    credentials_path = Path.home() / ".streamlit" / "credentials.toml"
    credentials_path.parent.mkdir(parents=True, exist_ok=True)

    # Only create if doesn't exist
    if not credentials_path.exists():
        credentials_path.write_text('[general]\nemail = ""\n')


def launch_web_ui(verbose: bool = False) -> None:
    """
    Launch Streamlit web interface in subprocess.

    Opens browser automatically to Streamlit UI.
    Blocks until user kills server (Ctrl+C).

    Args:
        verbose: Enable debug logging and console output

    Raises:
        RuntimeError: If Streamlit not installed or app file missing
    """
    # Get path to Streamlit app file
    app_file = Path(__file__).parent / "_web_app.py"

    if not app_file.exists():
        raise RuntimeError(f"Streamlit app file not found: {app_file}")

    # Verify streamlit is available
    try:
        import streamlit  # type: ignore  # noqa: F401
    except ImportError as e:
        raise RuntimeError("Streamlit not installed. Install with: uv sync") from e

    # Setup credentials to skip email prompt
    _setup_streamlit_config()

    # Set environment variables to disable telemetry
    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    # Print startup message
    print("\n🎯 Starting Amplifier Transcribe web interface...")
    print("   Browser will open automatically at http://localhost:8501")
    print("   Press Ctrl+C to stop the server")
    if verbose:
        print("   Verbose mode: Debug output enabled\n")
    else:
        print()

    # Build Streamlit command
    streamlit_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
    ]

    # Add verbose flags if enabled
    if verbose:
        streamlit_cmd.extend(["--logger.level", "debug"])

    try:
        # Launch Streamlit server (browser opens automatically)
        subprocess.run(
            streamlit_cmd,
            check=False,  # Don't raise on Ctrl+C
            env=env,
        )
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped. Thanks for using Amplifier Transcribe!")
    finally:
        print()
