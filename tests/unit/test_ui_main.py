import pytest
from meeting_recorder.ui.main_window import MeetRecorderApp

def test_main_window_initialization(qtbot):
    """Verify that the main window and its core components initialize correctly."""
    window = MeetRecorderApp()
    qtbot.addWidget(window)
    
    assert window.windowTitle() == "Meet-Recorder"
    assert window.sidebar is not None
    assert window.tabs.count() == 3
    assert window.tabs.tabText(0) == "History"
    assert window.tabs.tabText(1) == "Recording Control"
    assert window.tabs.tabText(2) == "Settings"
