"""
Web UI Launcher

Spawns Streamlit server for browser-based interface.
"""

import subprocess
import sys
from pathlib import Path


def launch_web_ui() -> None:
    """
    Launch Streamlit web interface in subprocess.

    Opens browser automatically to Streamlit UI.
    Blocks until user kills server (Ctrl+C).

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

    # Launch Streamlit server (browser opens automatically)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_file),
        ],
        check=False,  # Don't raise on Ctrl+C
    )
