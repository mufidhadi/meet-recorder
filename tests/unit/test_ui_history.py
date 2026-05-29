import os
import json
import pytest
from PyQt6.QtCore import Qt
from meeting_recorder.ui.main_window import MeetRecorderApp
from meeting_recorder.ui.models import RecordingSession

from unittest.mock import MagicMock
from PyQt6.QtMultimedia import QMediaPlayer

@pytest.fixture
def app(qtbot, tmp_path):
    # Setup mock recordings directory
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    
    session_id = "20260512_100000"
    session_dir = recordings_dir / session_id
    session_dir.mkdir()
    
    # Create mock transcript
    transcript_path = session_dir / "transcript.json"
    segments = [
        {"start": 0.0, "end": 1.0, "text": "Hello world", "speaker": "Speaker 0"},
        {"start": 1.5, "end": 2.5, "text": "Testing 123", "speaker": "Speaker 0"}
    ]
    with open(transcript_path, "w") as f:
        json.dump(segments, f)
        
    # Create mock summary
    summary_path = session_dir / "summary.md"
    with open(summary_path, "w") as f:
        f.write("# Summary\nThis is a test summary.")
        
    # Create mock audio (empty file is enough for check)
    audio_path = session_dir / "session_full.wav"
    audio_path.touch()
    
    # Override settings to use tmp recordings dir
    app = MeetRecorderApp()
    app.settings.output_dir = str(recordings_dir)
    app.session_manager.base_path = recordings_dir
    app.output_manager.base_dir = recordings_dir
    
    # Mock player to avoid issues with invalid WAV files
    app.player_bar.player.setPosition = MagicMock()
    app.player_bar.player.position = MagicMock(return_value=0)
    
    app._load_sessions()
    
    qtbot.addWidget(app)
    return app, session_id, str(session_dir)

def test_load_selected_session(app, qtbot):
    main_app, session_id, session_dir = app
    
    # Verify sidebar has the session
    assert main_app.sidebar.list_widget.count() == 1
    
    # Select the session
    item = main_app.sidebar.list_widget.item(0)
    main_app.sidebar.list_widget.setCurrentItem(item)
    
    # Check if HistoryTab loaded data
    assert main_app.history_tab.summary_view.toPlainText().strip() == "Summary\nThis is a test summary."
    # segments should be there
    assert len(main_app.history_tab._segment_widgets) == 2
    assert main_app.history_tab._segment_widgets[0].text == "Hello world"
    
    # Check if Tab switched to History
    assert main_app.tabs.currentIndex() == 0

def test_interactive_seeking(app, qtbot):
    main_app, session_id, session_dir = app
    
    # Select the session
    item = main_app.sidebar.list_widget.item(0)
    main_app.sidebar.list_widget.setCurrentItem(item)
    
    # Simulate click on first segment (starts at 0ms)
    widget = main_app.history_tab._segment_widgets[0]
    
    with qtbot.waitSignal(main_app.history_tab.seek_requested, timeout=1000) as blocker:
        qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)
    
    assert blocker.args == [0]
    # Player setPosition should be called
    main_app.player_bar.player.setPosition.assert_called_with(0)

    # Simulate click on second segment (starts at 1500ms)
    widget2 = main_app.history_tab._segment_widgets[1]
    with qtbot.waitSignal(main_app.history_tab.seek_requested, timeout=1000) as blocker:
        qtbot.mouseClick(widget2, Qt.MouseButton.LeftButton)
        
    assert blocker.args == [1500]
    main_app.player_bar.player.setPosition.assert_called_with(1500)
