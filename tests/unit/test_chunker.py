import io
import wave
import numpy as np
from meeting_recorder.processing.chunker import export_to_wav_bytes

def test_export_to_wav_bytes():
    data = np.zeros(16000, dtype=np.int16)
    wav_bytes = export_to_wav_bytes(data, 16000)
    
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 16000
