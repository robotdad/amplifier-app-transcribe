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

    # Setup credentials to skip email prompt
    _setup_streamlit_config()

    # Set environment variables to disable telemetry
    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

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
        env=env,
    )
