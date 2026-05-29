import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from meeting_recorder.ui.recording_tab import RecordingTab

def test_recording_tab_initialization(qtbot):
    tab = RecordingTab()
    qtbot.addWidget(tab)
    
    assert tab.start_button.isEnabled()
    assert not tab.stop_button.isEnabled()
    assert tab.timer_label.text() == "00:00:00"

def test_recording_tab_button_toggle(qtbot):
    tab = RecordingTab()
    qtbot.addWidget(tab)
    
    # Simulate clicking start
    qtbot.mouseClick(tab.start_button, Qt.MouseButton.LeftButton)
    
    assert not tab.start_button.isEnabled()
    assert tab.stop_button.isEnabled()
    
    # Simulate clicking stop
    qtbot.mouseClick(tab.stop_button, Qt.MouseButton.LeftButton)
    
    assert tab.start_button.isEnabled()
    assert not tab.stop_button.isEnabled()
