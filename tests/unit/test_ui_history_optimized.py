import os
import json
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from meeting_recorder.ui.history_tab import HistoryTab
from meeting_recorder.ui.models import RecordingSession

def test_highlight_at_time_optimized(qtbot, tmp_path):
    history_tab = HistoryTab()
    qtbot.addWidget(history_tab)
    
    # Setup mock session
    session_dir = tmp_path / "session1"
    session_dir.mkdir()
    
    transcript_path = session_dir / "transcript.json"
    segments = [
        {"start": 0.0, "text": "Segment 0"},
        {"start": 1.0, "text": "Segment 1"},
        {"start": 2.0, "text": "Segment 2"}
    ]
    with open(transcript_path, "w") as f:
        json.dump(segments, f)
        
    session = RecordingSession(session_id="20260512_100000", path=str(session_dir), has_transcript=True, has_summary=False)
    history_tab.load_session(session)
    
    assert len(history_tab._segment_widgets) == 3
    assert history_tab._segment_starts == [0, 1000, 2000]
    
    # Test highlight at 500ms -> should be segment 0
    history_tab.highlight_at_time(500)
    assert history_tab._last_highlighted_index == 0
    assert history_tab._segment_widgets[0]._is_highlighted is True
    assert history_tab._segment_widgets[1]._is_highlighted is False
    
    # Test highlight at 1500ms -> should be segment 1
    history_tab.highlight_at_time(1500)
    assert history_tab._last_highlighted_index == 1
    assert history_tab._segment_widgets[0]._is_highlighted is False
    assert history_tab._segment_widgets[1]._is_highlighted is True
    
    # Test highlight at 2500ms -> should be segment 2
    history_tab.highlight_at_time(2500)
    assert history_tab._last_highlighted_index == 2
    assert history_tab._segment_widgets[2]._is_highlighted is True

def test_load_session_resets_scroll(qtbot, tmp_path):
    history_tab = HistoryTab()
    # Force a large size and range
    history_tab.resize(400, 300)
    qtbot.addWidget(history_tab)
    
    # Add dummy widgets to enable scrolling
    for i in range(50):
        history_tab.transcript_layout.addWidget(QLabel("dummy"))
    
    # Wait for layout to process
    qtbot.waitExposed(history_tab)
    
    # Mock scroll position
    history_tab.scroll_area.verticalScrollBar().setRange(0, 1000)
    history_tab.scroll_area.verticalScrollBar().setValue(500)
    assert history_tab.scroll_area.verticalScrollBar().value() == 500
    
    # Setup mock session
    session_dir = tmp_path / "session2"
    session_dir.mkdir()
    transcript_path = session_dir / "transcript.json"
    with open(transcript_path, "w") as f:
        json.dump([], f)
        
    session = RecordingSession(session_id="20260512_110000", path=str(session_dir), has_transcript=True, has_summary=False)
    history_tab.load_session(session)
    
    assert history_tab.scroll_area.verticalScrollBar().value() == 0

def test_transcript_validation(qtbot, tmp_path):
    history_tab = HistoryTab()
    qtbot.addWidget(history_tab)
    
    session_dir = tmp_path / "session3"
    session_dir.mkdir()
    transcript_path = session_dir / "transcript.json"
    
    # Invalid format: dict instead of list
    with open(transcript_path, "w") as f:
        json.dump({"error": "not a list"}, f)
        
    session = RecordingSession(session_id="20260512_120000", path=str(session_dir), has_transcript=True, has_summary=False)
    history_tab.load_session(session)
    
    # Should show error message in layout
    assert history_tab.transcript_layout.count() > 0
    
    # Mixed valid/invalid segments
    with open(transcript_path, "w") as f:
        json.dump([
            {"start": 0.0, "text": "Valid"},
            {"invalid": "data"},
            {"start": 1.0} # Missing text
        ], f)
        
    history_tab.load_session(session)
    assert len(history_tab._segment_widgets) == 1
    assert history_tab._segment_widgets[0].text == "Valid"
