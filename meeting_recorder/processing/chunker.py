import io
import wave
import numpy as np
import threading
import time
from typing import Callable

def export_to_wav_bytes(data: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())
    return buf.getvalue()

def is_silent(data: np.ndarray, threshold: float = 0.01) -> bool:
    """Calculate RMS energy and check against threshold."""
    if len(data) == 0:
        return True
    
    # Convert to float32 for calculation to avoid overflow, normalize to -1.0 to 1.0
    float_data = data.astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(float_data**2))
    
    # Log actual RMS for debugging
    print(f"[CHUNKER] DEBUG: RMS = {rms:.6f} (Threshold = {threshold:.6f})")
    
    return float(rms) < threshold

class AudioChunker:
    def __init__(self, ring_buffer, chunk_duration_s: float, on_chunk_callback: Callable[[bytes, bool], None], silence_threshold: float = 0.01):
        self.ring_buffer = ring_buffer
        self.chunk_duration_s = chunk_duration_s
        self.on_chunk_callback = on_chunk_callback
        self.silence_threshold = silence_threshold
        self._stop_event = threading.Event()
        self._thread = None

    def _run(self):
        print(f"[CHUNKER] Thread started. Interval: {self.chunk_duration_s}s")
        while not self._stop_event.is_set():
            if self.ring_buffer.available_seconds >= self.chunk_duration_s:
                # Get the chunk data
                print(f"[CHUNKER] Extracting {self.chunk_duration_s}s chunk...")
                data = self.ring_buffer.get_last_n_seconds(self.chunk_duration_s)
                
                # Check for silence
                silent = is_silent(data, self.silence_threshold)
                
                if not silent:
                    # Convert to WAV
                    wav_bytes = export_to_wav_bytes(data, self.ring_buffer.sample_rate)
                    print(f"[CHUNKER] Chunk ready ({len(wav_bytes)} bytes). Triggering callback.")
                    # Trigger callback with data and silent=False
                    self.on_chunk_callback(wav_bytes, False)
                else:
                    print("[CHUNKER] Chunk is silent. Skipping transcription.")
                    # Trigger callback with empty bytes and silent=True
                    self.on_chunk_callback(b"", True)
                
                # Sleep for the duration of a chunk to avoid duplicate processing
                time.sleep(self.chunk_duration_s)
            else:
                time.sleep(0.5)
        print("[CHUNKER] Thread exiting.")

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
