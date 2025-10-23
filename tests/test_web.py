"""Tests for web UI launcher."""

from unittest.mock import Mock

import pytest  # type: ignore

from amplifier_app_transcribe.web import launch_web_ui


def test_launch_web_ui_spawns_streamlit(mocker, tmp_path):
    """launch_web_ui should spawn streamlit subprocess."""
    mock_run = mocker.patch("subprocess.run")

    # Mock streamlit import check
    mocker.patch.dict("sys.modules", {"streamlit": Mock()})

    # Create actual _web_app.py file for test
    mock_web_file = tmp_path / "web.py"
    mock_app_file = tmp_path / "_web_app.py"
    mock_app_file.write_text("# Mock Streamlit app")

    # Mock __file__ to point to our temp directory
    mocker.patch("amplifier_app_transcribe.web.__file__", str(mock_web_file))

    launch_web_ui()

    # Verify subprocess.run was called
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]

    # Verify command structure
    assert any("streamlit" in str(arg) for arg in args)
    assert "run" in args
    assert any("_web_app.py" in str(arg) for arg in args)


def test_launch_web_ui_fails_if_streamlit_missing(mocker):
    """launch_web_ui should raise error if streamlit not installed."""
    # Mock _web_app.py exists
    mock_path = mocker.patch("amplifier_app_transcribe.web.Path")
    mock_app_file = Mock()
    mock_app_file.exists.return_value = True
    mock_path.return_value.__truediv__.return_value = mock_app_file

    # Simulate ImportError when importing streamlit
    import builtins

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "streamlit":
            raise ImportError("No module named 'streamlit'")
        return real_import(name, *args, **kwargs)

    mocker.patch("builtins.__import__", side_effect=mock_import)

    with pytest.raises(RuntimeError, match="Streamlit not installed"):
        launch_web_ui()


def test_launch_web_ui_fails_if_app_file_missing(mocker, tmp_path):
    """launch_web_ui should raise error if _web_app.py missing."""
    # Mock __file__ to point to temp directory (no _web_app.py there)
    mock_web_file = tmp_path / "web.py"
    mocker.patch("amplifier_app_transcribe.web.__file__", str(mock_web_file))

    # Mock streamlit available
    mocker.patch.dict("sys.modules", {"streamlit": Mock()})

    with pytest.raises(RuntimeError, match="app file not found"):
        launch_web_ui()
