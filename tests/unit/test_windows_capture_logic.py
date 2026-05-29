import numpy as np
import pytest
import threading
import time
import collections
from unittest.mock import MagicMock, patch
from meeting_recorder.capture.windows import WindowsCaptureEngine
from meeting_recorder.data.audio import AudioConfig

@pytest.fixture
def audio_config():
    return AudioConfig(sample_rate=16000, channels=1)

def test_mixer_loop_logic(audio_config):
    """Test that the mixer loop correctly pulls from buffers and calls the callback."""
    received_chunks = []
    def callback(data):
        received_chunks.append(data)

    with patch('pyaudiowpatch.PyAudio'):
        engine = WindowsCaptureEngine(audio_config, callback)
        
        # Manually populate buffers
        chunk1 = np.array([1, 2, 3, 4], dtype=np.int16)
        chunk2 = np.array([10, 20, 30, 40], dtype=np.int16)
        
        # Mocking the stream parameters that would be set in start()
        engine._loopback_channels = 1
        engine._loopback_rate = 16000
        engine._mic_channels = 1
        engine._mic_rate = 16000
        
        # Start mixer thread manually or just mock it? 
        # Let's run it briefly.
        engine._stop_event.clear()
        mixer_thread = threading.Thread(target=engine._mixer_loop, daemon=True)
        
        with engine._lock:
            engine._loopback_buffer.append(chunk1)
            engine._mic_buffer.append(chunk2)
            
        mixer_thread.start()
        
        # Wait for mixer to process
        time.sleep(0.1)
        
        engine._stop_event.set()
        mixer_thread.join(timeout=1.0)
        
        assert len(received_chunks) > 0
        # Expected mixed is [11, 22, 33, 44]
        expected = np.array([11, 22, 33, 44], dtype=np.int16)
        np.testing.assert_array_equal(received_chunks[0], expected)

def test_mixer_loop_unaligned_chunks(audio_config):
    """Test that mixer handles chunks of different sizes by using residues."""
    received_chunks = []
    def callback(data):
        received_chunks.append(data)

    with patch('pyaudiowpatch.PyAudio'):
        engine = WindowsCaptureEngine(audio_config, callback)
        engine._loopback_channels = 1
        engine._mic_channels = 1
        
        # chunk1 is longer than chunk2
        chunk1 = np.array([1, 2, 3, 4, 5, 6], dtype=np.int16)
        chunk2 = np.array([10, 20, 30, 40], dtype=np.int16)
        
        engine._stop_event.clear()
        mixer_thread = threading.Thread(target=engine._mixer_loop, daemon=True)
        
        with engine._lock:
            engine._loopback_buffer.append(chunk1)
            engine._mic_buffer.append(chunk2)
            
        mixer_thread.start()
        time.sleep(0.1)
        
        # Only 4 samples should be mixed
        assert len(received_chunks) > 0
        expected = np.array([11, 22, 33, 44], dtype=np.int16)
        np.testing.assert_array_equal(received_chunks[0], expected)
        
        # Now add more mic data to process the residue
        chunk3 = np.array([50, 60], dtype=np.int16)
        with engine._lock:
            engine._mic_buffer.append(chunk3)
            
        time.sleep(0.1)
        
        engine._stop_event.set()
        mixer_thread.join(timeout=1.0)
        
        # Second chunk should be mixed: [5, 6] + [50, 60] = [55, 66]
        assert len(received_chunks) >= 2
        expected2 = np.array([55, 66], dtype=np.int16)
        np.testing.assert_array_equal(received_chunks[1], expected2)
