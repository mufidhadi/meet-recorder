import numpy as np
import pytest
from meeting_recorder.processing.audio import mix_audio

def test_mix_audio_summation():
    """Test that mixing two signals correctly sums their values."""
    # 10 samples of different values
    loopback = np.array([100, -100, 500, -500, 1000, -1000, 0, 0, 10, -10], dtype=np.int16)
    mic = np.array([50, -50, 200, -200, 1000, -1000, 5, -5, 10, -10], dtype=np.int16)
    
    expected = (loopback.astype(np.int32) + mic.astype(np.int32))
    expected = np.clip(expected, -32768, 32767).astype(np.int16)
    
    result = mix_audio(loopback, mic)
    np.testing.assert_array_equal(result, expected)

def test_mix_audio_clipping():
    """Test that mixing signals exceeding int16 range clips correctly."""
    loopback = np.array([30000, -30000], dtype=np.int16)
    mic = np.array([10000, -10000], dtype=np.int16)
    
    # Sums would be 40000 and -40000, which should clip to 32767 and -32768
    expected = np.array([32767, -32768], dtype=np.int16)
    
    result = mix_audio(loopback, mic)
    np.testing.assert_array_equal(result, expected)

def test_mix_audio_different_lengths():
    """Test that mixing signals of different lengths works by using the minimum length."""
    loopback = np.array([100, 200, 300], dtype=np.int16)
    mic = np.array([10, 20], dtype=np.int16)
    
    expected = np.array([110, 220], dtype=np.int16)
    
    result = mix_audio(loopback, mic)
    np.testing.assert_array_equal(result, expected)
