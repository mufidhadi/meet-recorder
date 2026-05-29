# Audio Chunker & Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menyelesaikan logic `AudioChunker` dan melakukan integrasi awal dengan `WindowsCaptureEngine` + `RingBuffer`.

**Architecture:** `AudioChunker` berjalan di thread terpisah, memantau `RingBuffer`, dan memicu callback saat data mencapai durasi tertentu.

**Tech Stack:** Python 3.12, numpy, threading.

---

### Task 3: Full AudioChunker

**Files:**
- Modify: `meeting_recorder/processing/chunker.py`
- Create: `scratch/test_audio_pipeline.py`

- [ ] **Step 1: Implement background chunking logic**
File: `meeting_recorder/processing/chunker.py`
```python
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

class AudioChunker:
    def __init__(self, ring_buffer, chunk_duration_s: float, on_chunk_callback: Callable[[bytes], None]):
        self.ring_buffer = ring_buffer
        self.chunk_duration_s = chunk_duration_s
        self.on_chunk_callback = on_chunk_callback
        self._stop_event = threading.Event()
        self._thread = None

    def _run(self):
        while not self._stop_event.is_set():
            if self.ring_buffer.available_seconds >= self.chunk_duration_s:
                data = self.ring_buffer.get_last_n_seconds(self.chunk_duration_s)
                # For MVP: We just grab the latest chunk. 
                # Improvement: Use a pointer to ensure no data is missed/duplicated.
                wav_bytes = export_to_wav_bytes(data, self.ring_buffer.sample_rate)
                self.on_chunk_callback(wav_bytes)
                
                # Wait for next chunk interval
                time.sleep(self.chunk_duration_s)
            else:
                time.sleep(0.5)

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
```

- [ ] **Step 2: Create Integration Script**
File: `scratch/test_audio_pipeline.py`
(Script ini akan menjalankan Engine -> Buffer -> Chunker dan menyimpan chunk pertama ke disk).

- [ ] **Step 3: Run Integration Test**
Run: `uv run scratch/test_audio_pipeline.py`
Expected: File `chunk_0.wav` muncul di folder root.

- [ ] **Step 4: Commit**
```bash
git add meeting_recorder/processing/chunker.py scratch/test_audio_pipeline.py
git commit -m "feat: complete AudioChunker and add integration test script"
```
