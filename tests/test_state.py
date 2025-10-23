"""
Tests for state management.
"""

from amplifier_app_transcribe.state import PipelineState, StateManager, VideoProcessingResult


def test_pipeline_state_creation():
    """Test creating a pipeline state."""
    state = PipelineState()
    assert state.stage == "initialized"
    assert state.total_videos == 0
    assert len(state.processed_videos) == 0
    assert len(state.failed_videos) == 0


def test_state_manager_initialization(tmp_path):
    """Test state manager initialization."""
    manager = StateManager(tmp_path / "session")
    assert manager.session_dir.exists()
    assert manager.state.stage == "initialized"
    # State file created on first save(), not during init
    assert not manager.state_file.exists()
    manager.save()
    assert manager.state_file.exists()


def test_state_persistence(tmp_path):
    """Test state saving and loading."""
    session_dir = tmp_path / "session"
    manager = StateManager(session_dir)

    # Add a processed video
    result = VideoProcessingResult(
        video_id="test123",
        source="https://example.com/video",
        status="success",
        output_dir=str(tmp_path / "output"),
        duration_seconds=120.0,
        cost_estimate=0.05,
    )
    manager.add_processed(result)

    # Create new manager pointing to same session
    manager2 = StateManager(session_dir)
    assert len(manager2.state.processed_videos) == 1
    assert manager2.state.processed_videos[0].video_id == "test123"


def test_is_already_processed(tmp_path):
    """Test checking if video is already processed."""
    manager = StateManager(tmp_path / "session")

    result = VideoProcessingResult(
        video_id="test123",
        source="https://example.com/video",
        status="success",
    )
    manager.add_processed(result)

    assert manager.is_already_processed("test123")
    assert not manager.is_already_processed("test456")


def test_get_pending_sources(tmp_path):
    """Test getting pending sources."""
    manager = StateManager(tmp_path / "session")
    manager.state.sources = ["video1", "video2", "video3"]

    # Process one video
    result = VideoProcessingResult(
        video_id="vid1",
        source="video1",
        status="success",
    )
    manager.add_processed(result)

    pending = manager.get_pending_sources()
    assert len(pending) == 2
    assert "video1" not in pending
    assert "video2" in pending
    assert "video3" in pending
