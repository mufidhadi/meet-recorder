# Dual Audio Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable recording of both system audio (loopback) and user voice (microphone) simultaneously by mixing them into a single 16kHz mono stream.

**Architecture:** Refactor `WindowsCaptureEngine` to manage two PyAudio streams. Process each stream into 16kHz mono, buffer them in thread-safe queues, and use a dedicated mixer thread to combine them using additive mixing with clipping protection.

**Tech Stack:** Python, PyAudioWPatch, NumPy, asyncio, threading.

---

### Task 1: Create Unit Test for Mixing Logic

**Files:**
- Create: `tests/unit/test_audio_mixer.py`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pytest

def mix_audio(loopback: np.ndarray, mic: np.ndarray) -> np.ndarray:
    # Placeholder for the mixing logic
    pass

def test_mix_audio_summation():
    # 10 samples of different values
    loopback = np.array([100, -100, 500, -500, 1000, -1000, 0, 0, 10, -10], dtype=np.int16)
    mic = np.array([50, -50, 200, -200, 1000, -1000, 5, -5, 10, -10], dtype=np.int16)
    
    expected = (loopback.astype(np.int32) + mic.astype(np.int32))
    expected = np.clip(expected, -32768, 32767).astype(np.int16)
    
    result = mix_audio(loopback, mic)
    np.testing.assert_array_equal(result, expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_audio_mixer.py`
Expected: FAIL (AssertionError or None return)

- [ ] **Step 3: Implement minimal mixing logic**

```python
import numpy as np

def mix_audio(loopback: np.ndarray, mic: np.ndarray) -> np.ndarray:
    # Ensure they are the same length for this utility
    n = min(len(loopback), len(mic))
    l = loopback[:n].astype(np.int32)
    m = mic[:n].astype(np.int32)
    mixed = np.clip(l + m, -32768, 32767)
    return mixed.astype(np.int16)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_audio_mixer.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_audio_mixer.py
git commit -m "test: add audio mixing logic unit test"
```

---

### Task 2: Refactor WindowsCaptureEngine Initialization & Stream Management

**Files:**
- Modify: `meeting_recorder/capture/windows.py`

- [ ] **Step 1: Update __init__ to include buffers and mixer thread**

```python
# Add imports
import queue
import collections

# Inside __init__
self._loopback_buffer = collections.deque(maxlen=16000 * 2) # 2 seconds of 16kHz samples
self._mic_buffer = collections.deque(maxlen=16000 * 2)
self._mixer_thread = None
self._lock = threading.Lock()
```

- [ ] **Step 2: Implement _process_stream_data helper**

```python
def _process_stream_data(self, in_data, n_channels, native_rate):
    raw_audio = np.frombuffer(in_data, dtype=np.int16)
    # Mono Mixdown
    if n_channels > 1:
        raw_audio = raw_audio.reshape(-1, n_channels).mean(axis=1).astype(np.int16)
    # Resample to 16kHz
    target_rate = self.config.sample_rate
    if native_rate != target_rate:
        skip = native_rate // target_rate
        return raw_audio[::skip]
    return raw_audio
```

- [ ] **Step 3: Update Callbacks**

```python
def _loopback_callback(self, in_data, frame_count, time_info, status):
    if self._stop_event.is_set(): return (None, pyaudio.paAbort)
    processed = self._process_stream_data(in_data, self._loopback_channels, self._loopback_rate)
    with self._lock:
        self._loopback_buffer.extend(processed.tolist())
    return (in_data, pyaudio.paContinue)

def _mic_callback(self, in_data, frame_count, time_info, status):
    if self._stop_event.is_set(): return (None, pyaudio.paAbort)
    processed = self._process_stream_data(in_data, self._mic_channels, self._mic_rate)
    with self._lock:
        self._mic_buffer.extend(processed.tolist())
    return (in_data, pyaudio.paContinue)
```

- [ ] **Step 4: Commit**

```bash
git add meeting_recorder/capture/windows.py
git commit -m "refactor: add dual buffers and stream callbacks to WindowsCaptureEngine"
```

---

### Task 3: Implement Mixer Thread & Start/Stop Logic

**Files:**
- Modify: `meeting_recorder/capture/windows.py`

- [ ] **Step 1: Implement _mixer_loop**

```python
def _mixer_loop(self):
    while not self._stop_event.is_set():
        with self._lock:
            n = min(len(self._loopback_buffer), len(self._mic_buffer))
            if n > 0:
                l_chunk = np.array([self._loopback_buffer.popleft() for _ in range(n)], dtype=np.int32)
                m_chunk = np.array([self._mic_buffer.popleft() for _ in range(n)], dtype=np.int32)
                mixed = np.clip(l_chunk + m_chunk, -32768, 32767).astype(np.int16)
                self.callback(mixed)
        import time
        time.sleep(0.05) # 50ms interval
```

- [ ] **Step 2: Update start() to open both streams and start mixer**

```python
# Open loopback (existing logic but update rate/channels storage)
# Open mic (similar to loopback)
# Start both streams
# Start self._mixer_thread
```

- [ ] **Step 3: Update stop() to cleanup everything**

```bash
# Set stop event
# Stop/Close both streams
# Join mixer thread
```

- [ ] **Step 4: Verify with scratch/test_dual_capture.py**

Run: `uv run python scratch/test_dual_capture.py`
Expected: Generates `test_mixed.wav` containing both audio sources.

- [ ] **Step 5: Commit**

```bash
git add meeting_recorder/capture/windows.py
git commit -m "feat: implement mixer loop and dual stream start/stop"
```

---

### Task 4: Final Verification with record.cmd

**Files:**
- Run: `record.cmd`

- [ ] **Step 1: Record a short meeting segment**
- [ ] **Step 2: Playback the recorded .wav in `recordings/`**
- [ ] **Step 3: Verify user voice is audible**
- [ ] **Step 4: Verify transcription contains user's speech**
- [ ] **Step 5: Final Commit & Report**
