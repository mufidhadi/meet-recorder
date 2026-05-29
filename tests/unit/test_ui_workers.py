import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtTest import QSignalSpy
from meeting_recorder.ui.workers import RecordingWorker
from meeting_recorder.data.audio import AudioConfig

@pytest.fixture
def mock_config():
    return AudioConfig(sample_rate=16000, channels=1)

@pytest.fixture
def mock_dependencies():
    return {
        'settings': MagicMock(),
        'output_manager': MagicMock(),
        'ring_buffer': MagicMock(),
        'transcriber': MagicMock(),
        'aggregator': MagicMock(),
        'engine_class': MagicMock(),
        'chunker_class': MagicMock()
    }

def test_recording_worker_initialization(mock_config, mock_dependencies):
    worker = RecordingWorker(
        config=mock_config,
        **mock_dependencies
    )
    assert worker is not None
    assert not worker.isRunning()

def test_recording_worker_signals(mock_config, mock_dependencies, qtbot):
    worker = RecordingWorker(
        config=mock_config,
        **mock_dependencies
    )
    
    vu_spy = QSignalSpy(worker.vu_levels)
    timer_spy = QSignalSpy(worker.timer_tick)
    transcription_spy = QSignalSpy(worker.transcription_received)
    
    # Simulate a VU level update
    worker._on_vu_levels(0.5, 0.3)
    assert len(vu_spy) == 1
    assert vu_spy[0] == [0.5, 0.3]
    
    # Simulate a timer tick
    worker._on_timer_tick()
    assert len(timer_spy) == 1
    assert isinstance(timer_spy[0][0], str)
