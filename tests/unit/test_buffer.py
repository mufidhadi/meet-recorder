import numpy as np
import pytest
from meeting_recorder.processing.buffer import RingBuffer

def test_ring_buffer_push_pop():
    buf = RingBuffer(maxsize_seconds=1, sample_rate=1000)
    data = np.ones(500, dtype=np.int16)
    buf.push(data)
    assert buf.available_seconds == 0.5
    
    retrieved = buf.get_last_n_seconds(0.2)
    assert len(retrieved) == 200
    assert np.all(retrieved == 1)
