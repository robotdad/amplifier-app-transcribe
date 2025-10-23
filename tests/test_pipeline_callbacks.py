"""Tests for pipeline progress callback functionality."""

from unittest.mock import Mock

from amplifier_app_transcribe.pipeline import TranscriptionPipeline


def test_pipeline_accepts_callback():
    """Pipeline should accept on_progress callback parameter."""
    callback = Mock()
    pipeline = TranscriptionPipeline(on_progress=callback)
    assert pipeline.on_progress == callback


def test_pipeline_without_callback_still_works():
    """Pipeline should work normally when callback is None (CLI mode)."""
    pipeline = TranscriptionPipeline(on_progress=None)
    assert pipeline.on_progress is None
    # Should initialize without errors - verified by no exception


def test_report_progress_calls_callback():
    """_report_progress should invoke callback with stage and data."""
    callback = Mock()
    pipeline = TranscriptionPipeline(on_progress=callback)

    # Call _report_progress
    pipeline._report_progress("loading", {"source": "test.mp4"})

    # Verify callback was called
    callback.assert_called_once_with("loading", {"source": "test.mp4"})


def test_report_progress_without_callback_does_not_crash():
    """_report_progress should not crash when callback is None."""
    pipeline = TranscriptionPipeline(on_progress=None)

    # Should not raise - callback is None
    pipeline._report_progress("loading", {"source": "test.mp4"})


def test_report_progress_handles_callback_exceptions():
    """_report_progress should catch and log callback exceptions."""

    def bad_callback(stage, data):
        raise ValueError("Callback failed")

    pipeline = TranscriptionPipeline(on_progress=bad_callback)

    # Should not raise - exceptions are caught
    pipeline._report_progress("loading", {"source": "test.mp4"})


def test_report_progress_with_none_data():
    """_report_progress should handle None data parameter."""
    callback = Mock()
    pipeline = TranscriptionPipeline(on_progress=callback)

    # Call with None data
    pipeline._report_progress("loading", None)

    # Verify callback called with empty dict
    callback.assert_called_once_with("loading", {})
