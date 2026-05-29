import pytest
import os
import shutil
from pathlib import Path
from meeting_recorder.ui.models import SessionManager, RecordingSession

@pytest.fixture
def mock_recordings(tmp_path):
    """Create a mock recordings directory with some sessions."""
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    
    # Session 1: Both transcript and summary
    s1 = recordings_dir / "20260512_140000"
    s1.mkdir()
    (s1 / "transcript.json").write_text("{}")
    (s1 / "summary.md").write_text("# Summary")
    
    # Session 2: Only transcript
    s2 = recordings_dir / "20260512_150000"
    s2.mkdir()
    (s2 / "transcript.json").write_text("{}")
    
    # Session 3: Neither (just audio maybe, but for our check only transcript/summary)
    s3 = recordings_dir / "20260511_100000"
    s3.mkdir()
    
    return recordings_dir

def test_session_manager_list_sessions(mock_recordings):
    manager = SessionManager(base_path=str(mock_recordings))
    sessions = manager.get_sessions()
    
    assert len(sessions) == 3
    # Check sorting (descending)
    assert sessions[0].session_id == "20260512_150000"
    assert sessions[1].session_id == "20260512_140000"
    assert sessions[2].session_id == "20260511_100000"
    
    # Check flags
    assert sessions[1].has_transcript is True
    assert sessions[1].has_summary is True
    
    assert sessions[0].has_transcript is True
    assert sessions[0].has_summary is False
    
    assert sessions[2].has_transcript is False
    assert sessions[2].has_summary is False

def test_sidebar_widget_population(qtbot, mock_recordings):
    from meeting_recorder.ui.sidebar import SidebarWidget
    from meeting_recorder.ui.models import SessionManager
    
    manager = SessionManager(base_path=str(mock_recordings))
    widget = SidebarWidget()
    qtbot.addWidget(widget)
    
    sessions = manager.get_sessions()
    widget.set_sessions(sessions)
    
    assert widget.list_widget.count() == 3
    # Check first item text (20260512_150000 -> 12 May 2026, 15:00)
    # The exact format might vary slightly depending on implementation, but let's check for keywords
    item_text = widget.list_widget.item(0).text()
    assert "12 May 2026" in item_text
    assert "15:00" in item_text
