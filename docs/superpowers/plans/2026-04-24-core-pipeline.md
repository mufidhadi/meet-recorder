# Core Audio Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun fondasi audio capture, buffering, dan chunking untuk Windows (WASAPI).

**Architecture:** Menggunakan `pyaudiowpatch` untuk capture, `RingBuffer` berbasis NumPy untuk thread-safe storage, dan `AudioChunker` untuk export WAV bytes.

**Tech Stack:** Python 3.12, uv, pyaudiowpatch, numpy, pytest.

---

### Task 1: Environment & Config Setup

**Files:**
- Modify: `pyproject.toml`
- Create: `meeting_recorder/config/settings.py`
- Create: `meeting_recorder/data/audio.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Update dependencies**
Run: `uv add pydantic pydantic-settings numpy sounddevice pyaudiowpatch`

- [ ] **Step 2: Create AudioConfig dataclass**
File: `meeting_recorder/data/audio.py`
```python
from dataclasses import dataclass

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16
    capture_microphone: bool = True
    capture_system_audio: bool = True
```

- [ ] **Step 3: Create Pydantic Settings**
File: `meeting_recorder/config/settings.py`
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from meeting_recorder.data.audio import AudioConfig

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    audio: AudioConfig = AudioConfig()
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    output_dir: str = "./recordings"
```

- [ ] **Step 4: Commit**
```bash
git add pyproject.toml meeting_recorder/
git commit -m "chore: setup dependencies and basic config models"
```

---

### Task 2: Implement RingBuffer

**Files:**
- Create: `meeting_recorder/processing/buffer.py`
- Test: `tests/unit/test_buffer.py`

- [ ] **Step 1: Write failing test for RingBuffer**
File: `tests/unit/test_buffer.py`
```python
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/unit/test_buffer.py`

- [ ] **Step 3: Implement RingBuffer**
File: `meeting_recorder/processing/buffer.py`
```python
import numpy as np
import threading

class RingBuffer:
    def __init__(self, maxsize_seconds: float, sample_rate: int):
        self.sample_rate = sample_rate
        self.max_samples = int(maxsize_seconds * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.int16)
        self.write_index = 0
        self.size = 0
        self.lock = threading.Lock()

    def push(self, data: np.ndarray):
        with self.lock:
            n = len(data)
            if n > self.max_samples:
                data = data[-self.max_samples:]
                n = self.max_samples
            
            end_space = self.max_samples - self.write_index
            if n <= end_space:
                self.buffer[self.write_index:self.write_index + n] = data
            else:
                self.buffer[self.write_index:] = data[:end_space]
                self.buffer[:n - end_space] = data[end_space:]
            
            self.write_index = (self.write_index + n) % self.max_samples
            self.size = min(self.size + n, self.max_samples)

    def get_last_n_seconds(self, n_seconds: float) -> np.ndarray:
        with self.lock:
            n_samples = int(n_seconds * self.sample_rate)
            n_samples = min(n_samples, self.size)
            
            start = (self.write_index - n_samples) % self.max_samples
            if start + n_samples <= self.max_samples:
                return self.buffer[start:start + n_samples].copy()
            else:
                part1 = self.buffer[start:]
                part2 = self.buffer[:n_samples - len(part1)]
                return np.concatenate([part1, part2])

    @property
    def available_seconds(self) -> float:
        return self.size / self.sample_rate
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/unit/test_buffer.py`

- [ ] **Step 5: Commit**
```bash
git add meeting_recorder/processing/buffer.py tests/unit/test_buffer.py
git commit -m "feat: implement thread-safe RingBuffer using NumPy"
```

---

### Task 3: Implement AudioChunker

**Files:**
- Create: `meeting_recorder/processing/chunker.py`
- Test: `tests/unit/test_chunker.py`

- [ ] **Step 1: Write test for WAV export**
File: `tests/unit/test_chunker.py`
```python
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
```

- [ ] **Step 2: Implement export and Chunker logic**
File: `meeting_recorder/processing/chunker.py`
```python
import io
import wave
import numpy as np

def export_to_wav_bytes(data: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())
    return buf.getvalue()

class AudioChunker:
    # Logic to periodically grab from buffer and trigger on_chunk callback
    pass
```

- [ ] **Step 3: Commit**
```bash
git add meeting_recorder/processing/chunker.py tests/unit/test_chunker.py
git commit -m "feat: implement WAV export utility"
```
