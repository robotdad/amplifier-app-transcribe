"""
Tests for transcript formatting.
"""

from amplifier_app_transcribe.formatter import (
    _add_paragraph_breaks,
    _build_continuous_text_with_timestamps,
    _extract_youtube_id,
    _format_duration,
    _is_youtube_url,
)


def test_format_duration():
    """Test duration formatting."""
    assert _format_duration(30) == "00:30"
    assert _format_duration(90) == "01:30"
    assert _format_duration(3661) == "01:01:01"


def test_is_youtube_url():
    """Test YouTube URL detection."""
    assert _is_youtube_url("https://www.youtube.com/watch?v=abc123")
    assert _is_youtube_url("https://youtu.be/abc123")
    assert not _is_youtube_url("https://example.com/video")


def test_extract_youtube_id():
    """Test YouTube ID extraction."""
    assert _extract_youtube_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert _extract_youtube_id("https://youtu.be/xyz789") == "xyz789"
    assert _extract_youtube_id("https://example.com") is None


def test_add_paragraph_breaks():
    """Test paragraph break insertion."""
    # Short text - no breaks
    text = "This is sentence one. This is sentence two."
    result = _add_paragraph_breaks(text)
    assert "\n\n" not in result

    # Long text - should have breaks
    sentences = [f"This is sentence {i}." for i in range(10)]
    text = " ".join(sentences)
    result = _add_paragraph_breaks(text)
    assert "\n\n" in result


def test_build_continuous_text_with_timestamps():
    """Test continuous text building with timestamps."""

    class MockSegment:
        def __init__(self, start, text):
            self.start = start
            self.text = text

    segments = [
        MockSegment(0, "First segment"),
        MockSegment(35, "Second segment after 35 seconds"),
        MockSegment(70, "Third segment after 70 seconds"),
    ]

    result = _build_continuous_text_with_timestamps(segments, None, 30)

    # Should have timestamps at 35 and 70 seconds
    assert "[00:35]" in result or "[01:10]" in result
    assert "First segment" in result
    assert "Second segment" in result
