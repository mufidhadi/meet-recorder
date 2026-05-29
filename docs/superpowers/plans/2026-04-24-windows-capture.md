# Windows Capture Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi `WindowsCaptureEngine` untuk menangkap system audio (loopback) dan microphone menggunakan `pyaudiowpatch`.

**Architecture:** Menggunakan dual-stream capture yang di-mix secara linear dalam callback. Output dikirim ke `RingBuffer`.

**Tech Stack:** Python 3.12, pyaudiowpatch, numpy.

---

### Task 4: Windows Capture Engine

**Files:**
- Create: `meeting_recorder/capture/engine.py` (ABC)
- Create: `meeting_recorder/capture/windows.py`
- Create: `scratch/check_audio_devices.py` (Manual test)

- [ ] **Step 1: Create Engine ABC**
File: `meeting_recorder/capture/engine.py`
```python
from abc import ABC, abstractmethod
from typing import Callable
import numpy as np
from meeting_recorder.data.audio import AudioConfig

class CaptureEngine(ABC):
    def __init__(self, config: AudioConfig, callback: Callable[[np.ndarray], None]):
        self.config = config
        self.callback = callback
        self._is_active = False

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @property
    def is_active(self) -> bool:
        return self._is_active
```

- [ ] **Step 2: Create device discovery script**
File: `scratch/check_audio_devices.py`
```python
import pyaudiowpatch as pyaudio

def list_wasapi_devices():
    p = pyaudio.PyAudio()
    try:
        print("WASAPI Devices:")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev.get('hostApi') == p.get_host_api_info_by_type(pyaudio.paWASAPI).get('index'):
                print(f"ID {i}: {dev.get('name')} (Loopback: {dev.get('isLoopbackDevice', False)})")
    finally:
        p.terminate()

if __name__ == "__main__":
    list_wasapi_devices()
```

- [ ] **Step 3: Run discovery script**
Run: `uv run scratch/check_audio_devices.py`
Expected: Daftar device WASAPI muncul, termasuk loopback.

- [ ] **Step 4: Implement WindowsCaptureEngine**
File: `meeting_recorder/capture/windows.py`
(Akan menggunakan `pyaudiowpatch` untuk membuka stream loopback + mic dan melakukan mixing di callback).

- [ ] **Step 5: Commit**
```bash
git add meeting_recorder/capture/ scratch/
git commit -m "feat: implement windows capture engine with WASAPI loopback"
```
