# 02 — Technical Design Document (TDD)

> **Versi:** 1.0  
> **Tanggal:** April 2026  
> **Status:** Draft

---

## 1. Struktur Proyek

```
meeting-recorder/
├── README.md
├── pyproject.toml              # Dependency management (uv / pip)
├── .env.example                # Template environment variables
├── config.yaml                 # Konfigurasi utama
│
├── src/
│   └── meeting_recorder/
│       ├── __init__.py
│       ├── main.py             # Entry point CLI
│       │
│       ├── capture/
│       │   ├── __init__.py
│       │   ├── engine.py       # AudioCaptureEngine
│       │   ├── windows.py      # WASAPI Loopback implementation
│       │   ├── macos.py        # ScreenCaptureKit / BlackHole impl
│       │   └── linux.py        # PulseAudio monitor implementation
│       │
│       ├── processing/
│       │   ├── __init__.py
│       │   ├── chunker.py      # AudioChunker
│       │   ├── buffer.py       # RingBuffer thread-safe
│       │   └── vad.py          # Voice Activity Detection (opsional)
│       │
│       ├── transcription/
│       │   ├── __init__.py
│       │   ├── engine.py       # TranscriptionEngine (abstract)
│       │   ├── whisper_api.py  # OpenAI Whisper API client
│       │   └── whisper_local.py# faster-whisper local client
│       │
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── aggregator.py   # TranscriptAggregator
│       │   ├── summarizer.py   # LLMSummarizer (abstract)
│       │   ├── gemini.py       # Google Gemini implementation
│       │   └── openai_llm.py   # OpenAI GPT implementation
│       │
│       ├── output/
│       │   ├── __init__.py
│       │   └── manager.py      # OutputManager
│       │
│       └── config/
│           ├── __init__.py
│           └── settings.py     # Pydantic settings
│
└── tests/
    ├── unit/
    │   ├── test_chunker.py
    │   ├── test_aggregator.py
    │   └── test_summarizer.py
    └── integration/
        └── test_pipeline.py
```

---

## 2. Desain Modul Detail

### 2.1 `AudioCaptureEngine` (`capture/engine.py`)

**Tanggung Jawab:** Abstraksi untuk semua platform, menyediakan interface yang seragam ke layer atas.

```python
# Interface / Abstract Base Class
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from typing import Callable, Optional

@dataclass
class AudioConfig:
    sample_rate: int = 16000       # Hz — Whisper optimal
    channels: int = 1              # Mono
    dtype: str = "int16"           # 16-bit PCM
    chunk_frames: int = 1024       # Frame per callback
    capture_system_audio: bool = True
    capture_microphone: bool = True
    mic_device_index: Optional[int] = None
    system_device_index: Optional[int] = None

# Callback type: dipanggil setiap ada audio chunk baru
AudioCallback = Callable[[np.ndarray], None]

class AudioCaptureEngine(ABC):
    def __init__(self, config: AudioConfig, callback: AudioCallback):
        self.config = config
        self.callback = callback
        self._is_recording = False

    @abstractmethod
    def list_devices(self) -> list[dict]:
        """List semua audio device yang tersedia."""
        ...

    @abstractmethod
    def start(self) -> None:
        """Mulai capture audio."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Hentikan capture audio."""
        ...

    @property
    def is_recording(self) -> bool:
        return self._is_recording
```

**Platform Factory:**
```python
# capture/engine.py
import platform

def create_capture_engine(config: AudioConfig, callback: AudioCallback) -> AudioCaptureEngine:
    system = platform.system()
    if system == "Windows":
        from .windows import WindowsCaptureEngine
        return WindowsCaptureEngine(config, callback)
    elif system == "Darwin":
        from .macos import MacOSCaptureEngine
        return MacOSCaptureEngine(config, callback)
    elif system == "Linux":
        from .linux import LinuxCaptureEngine
        return LinuxCaptureEngine(config, callback)
    else:
        raise NotImplementedError(f"Platform {system} tidak didukung")
```

---

### 2.2 Windows Implementation (`capture/windows.py`)

**Library:** `pyaudiowpatch` — Fork PyAudio yang mendukung WASAPI Loopback.

```
pip install pyaudiowpatch
```

**Cara kerja WASAPI Loopback:**
- Windows menyediakan "loopback device" — virtual device yang merekam output dari speaker.
- `pyaudiowpatch` mengekspos device ini sebagai input device biasa.
- Kita mix loopback (system audio) dengan microphone secara manual.

```python
# capture/windows.py
import pyaudiowpatch as pyaudio
import numpy as np
import threading
from .engine import AudioCaptureEngine, AudioConfig, AudioCallback

class WindowsCaptureEngine(AudioCaptureEngine):
    def __init__(self, config: AudioConfig, callback: AudioCallback):
        super().__init__(config, callback)
        self._pa = pyaudio.PyAudio()
        self._system_stream = None
        self._mic_stream = None
        self._mix_buffer = {}       # {stream_id: latest_chunk}
        self._lock = threading.Lock()

    def list_devices(self) -> list[dict]:
        devices = []
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            devices.append({
                "index": i,
                "name": info["name"],
                "is_loopback": info.get("isLoopbackDevice", False),
                "max_input_channels": info["maxInputChannels"],
            })
        return devices

    def _find_loopback_device(self) -> int:
        """Auto-detect WASAPI loopback device dari default output."""
        wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speaker_idx = wasapi_info["defaultOutputDevice"]
        
        # Cari loopback device yang berkorespondensi
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if (info.get("isLoopbackDevice") and 
                info["name"].startswith(
                    self._pa.get_device_info_by_index(default_speaker_idx)["name"]
                )):
                return i
        raise RuntimeError("Tidak ditemukan WASAPI loopback device")

    def _audio_callback(self, stream_id: str):
        """Return callback function untuk stream tertentu."""
        def callback(in_data, frame_count, time_info, status):
            audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
            audio /= 32768.0  # Normalize ke [-1.0, 1.0]
            
            with self._lock:
                self._mix_buffer[stream_id] = audio
                
                # Jika kedua stream sudah ada, mix dan emit
                if len(self._mix_buffer) == 2:
                    chunks = list(self._mix_buffer.values())
                    min_len = min(len(c) for c in chunks)
                    mixed = sum(c[:min_len] for c in chunks) / len(chunks)
                    
                    # Clip dan convert kembali ke int16
                    mixed = np.clip(mixed, -1.0, 1.0)
                    output = (mixed * 32768).astype(np.int16)
                    self.callback(output)
                    self._mix_buffer.clear()
            
            return (None, pyaudio.paContinue)
        return callback

    def start(self) -> None:
        loopback_idx = (self.config.system_device_index or 
                        self._find_loopback_device())
        
        # Stream untuk system audio (loopback)
        if self.config.capture_system_audio:
            self._system_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=loopback_idx,
                frames_per_buffer=self.config.chunk_frames,
                stream_callback=self._audio_callback("system"),
            )

        # Stream untuk microphone
        if self.config.capture_microphone:
            self._mic_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.config.mic_device_index,
                frames_per_buffer=self.config.chunk_frames,
                stream_callback=self._audio_callback("mic"),
            )

        self._is_recording = True

    def stop(self) -> None:
        for stream in [self._system_stream, self._mic_stream]:
            if stream:
                stream.stop_stream()
                stream.close()
        self._pa.terminate()
        self._is_recording = False
```

---

### 2.3 macOS Implementation (`capture/macos.py`)

**Dua opsi di macOS:**

**Opsi A (Direkomendasikan): BlackHole Virtual Audio Device**
- Install BlackHole: `brew install blackhole-2ch`
- Buat Multi-Output Device di Audio MIDI Setup: gabungkan BlackHole + Speaker asli
- Set Multi-Output sebagai default output
- Capture dari BlackHole sebagai input

```python
# capture/macos.py — dengan BlackHole
import sounddevice as sd
import numpy as np
from .engine import AudioCaptureEngine, AudioConfig, AudioCallback

class MacOSCaptureEngine(AudioCaptureEngine):
    BLACKHOLE_NAME = "BlackHole 2ch"

    def _find_blackhole_device(self) -> int:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if self.BLACKHOLE_NAME in dev["name"] and dev["max_input_channels"] > 0:
                return i
        raise RuntimeError(
            f"BlackHole tidak ditemukan. Install dengan: brew install blackhole-2ch\n"
            f"Lalu buat Multi-Output Device di Audio MIDI Setup."
        )

    def start(self) -> None:
        blackhole_idx = (self.config.system_device_index or 
                         self._find_blackhole_device())
        
        def callback(indata, frames, time, status):
            self.callback(indata[:, 0].copy())  # Ambil channel pertama (mono)

        self._stream = sd.InputStream(
            device=blackhole_idx,
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="int16",
            callback=callback,
            blocksize=self.config.chunk_frames,
        )
        self._stream.start()
        self._is_recording = True

    def stop(self) -> None:
        if hasattr(self, "_stream"):
            self._stream.stop()
            self._stream.close()
        self._is_recording = False

    def list_devices(self) -> list[dict]:
        return [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0
        ]
```

**Opsi B: ScreenCaptureKit (macOS 13+)**
- Tidak perlu virtual audio device
- Butuh helper Swift/Objective-C atau tool `screcord`
- Lebih complex tapi tidak perlu instalasi tambahan user
- Lihat: `https://developer.apple.com/documentation/screencapturekit`

---

### 2.4 Linux Implementation (`capture/linux.py`)

**Library:** `sounddevice` dengan PulseAudio `monitor` source.

```python
# capture/linux.py
import sounddevice as sd
import subprocess
import numpy as np
from .engine import AudioCaptureEngine, AudioConfig, AudioCallback

class LinuxCaptureEngine(AudioCaptureEngine):
    def _find_monitor_source(self) -> str:
        """Cari PulseAudio monitor source dari default sink."""
        result = subprocess.run(
            ["pactl", "get-default-sink"], capture_output=True, text=True
        )
        default_sink = result.stdout.strip()
        return f"{default_sink}.monitor"

    def start(self) -> None:
        monitor_name = (
            self.config.system_device_index or self._find_monitor_source()
        )

        def callback(indata, frames, time, status):
            self.callback(indata[:, 0].copy())

        self._stream = sd.InputStream(
            device=monitor_name,
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="int16",
            callback=callback,
            blocksize=self.config.chunk_frames,
        )
        self._stream.start()
        self._is_recording = True

    def stop(self) -> None:
        if hasattr(self, "_stream"):
            self._stream.stop()
            self._stream.close()
        self._is_recording = False

    def list_devices(self) -> list[dict]:
        return [
            {"index": i, "name": d["name"]}
            for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0
        ]
```

---

### 2.5 `RingBuffer` (`processing/buffer.py`)

Thread-safe ring buffer untuk menjembatani audio capture thread dan processing thread.

```python
import threading
import numpy as np
from collections import deque

class RingBuffer:
    """Thread-safe audio ring buffer."""
    
    def __init__(self, maxsize_seconds: float, sample_rate: int):
        self._maxsize = int(maxsize_seconds * sample_rate)
        self._buffer = deque(maxlen=self._maxsize)
        self._lock = threading.Lock()
        self._data_event = threading.Event()

    def push(self, data: np.ndarray) -> None:
        with self._lock:
            self._buffer.extend(data.tolist())
        self._data_event.set()

    def pop(self, n_samples: int, timeout: float = 1.0) -> np.ndarray | None:
        self._data_event.wait(timeout=timeout)
        with self._lock:
            if len(self._buffer) < n_samples:
                return None
            samples = [self._buffer.popleft() for _ in range(n_samples)]
            if len(self._buffer) == 0:
                self._data_event.clear()
            return np.array(samples, dtype=np.int16)

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)
```

---

### 2.6 `AudioChunker` (`processing/chunker.py`)

Memotong buffer menjadi chunks dengan overlap untuk menghindari kata terpotong.

```python
import numpy as np
import io
import wave
import threading
from .buffer import RingBuffer

class AudioChunker:
    def __init__(
        self,
        ring_buffer: RingBuffer,
        sample_rate: int = 16000,
        chunk_duration_s: float = 30.0,
        overlap_s: float = 2.0,
        on_chunk: callable = None,  # Callback: (wav_bytes, chunk_index) -> None
    ):
        self.ring_buffer = ring_buffer
        self.sample_rate = sample_rate
        self.chunk_samples = int(chunk_duration_s * sample_rate)
        self.overlap_samples = int(overlap_s * sample_rate)
        self.on_chunk = on_chunk
        self._chunk_index = 0
        self._overlap_data = np.array([], dtype=np.int16)
        self._running = False
        self._thread = None

    def _samples_to_wav(self, samples: np.ndarray) -> bytes:
        """Convert numpy array ke WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(samples.tobytes())
        return buf.getvalue()

    def _process_loop(self):
        while self._running:
            samples = self.ring_buffer.pop(
                self.chunk_samples - len(self._overlap_data),
                timeout=1.0
            )
            if samples is None:
                continue

            # Gabungkan overlap dari chunk sebelumnya
            if len(self._overlap_data) > 0:
                chunk = np.concatenate([self._overlap_data, samples])
            else:
                chunk = samples

            # Simpan overlap untuk chunk berikutnya
            self._overlap_data = chunk[-self.overlap_samples:].copy()

            # Emit chunk
            if self.on_chunk:
                wav_bytes = self._samples_to_wav(chunk)
                self.on_chunk(wav_bytes, self._chunk_index)
                self._chunk_index += 1

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
```

---

### 2.7 `TranscriptionEngine` (`transcription/engine.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TranscriptSegment:
    chunk_index: int
    start_time: float        # detik dari awal recording
    end_time: float
    text: str
    confidence: float = 1.0
    language: str = "id"     # default: Indonesian

class TranscriptionEngine(ABC):
    @abstractmethod
    async def transcribe(
        self, 
        wav_bytes: bytes, 
        chunk_index: int,
        offset_seconds: float = 0.0,
    ) -> list[TranscriptSegment]:
        ...
```

**Whisper API Implementation:**
```python
# transcription/whisper_api.py
from openai import AsyncOpenAI
from .engine import TranscriptionEngine, TranscriptSegment
import io

class WhisperAPITranscriber(TranscriptionEngine):
    def __init__(self, api_key: str, language: str = "id", prompt: str = ""):
        self.client = AsyncOpenAI(api_key=api_key)
        self.language = language
        self.prompt = prompt  # Prompt bisa bantu akurasi nama/istilah

    async def transcribe(
        self,
        wav_bytes: bytes,
        chunk_index: int,
        offset_seconds: float = 0.0,
    ) -> list[TranscriptSegment]:
        # Whisper API menerima file-like object
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = f"chunk_{chunk_index}.wav"

        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=self.language,
            response_format="verbose_json",  # Dapatkan timestamp
            timestamp_granularities=["segment"],
            prompt=self.prompt,
        )

        segments = []
        for seg in response.segments:
            segments.append(TranscriptSegment(
                chunk_index=chunk_index,
                start_time=offset_seconds + seg.start,
                end_time=offset_seconds + seg.end,
                text=seg.text.strip(),
                language=response.language,
            ))
        return segments
```

**Local Whisper Implementation:**
```python
# transcription/whisper_local.py
# pip install faster-whisper
from faster_whisper import WhisperModel
from .engine import TranscriptionEngine, TranscriptSegment
import io
import tempfile, os

class WhisperLocalTranscriber(TranscriptionEngine):
    def __init__(
        self, 
        model_size: str = "medium",   # tiny, base, small, medium, large-v3
        device: str = "auto",          # auto, cpu, cuda
        language: str = "id",
    ):
        self.language = language
        # Model di-cache setelah download pertama
        self.model = WhisperModel(
            model_size, 
            device=device,
            compute_type="int8",       # Hemat VRAM/RAM
        )

    async def transcribe(
        self,
        wav_bytes: bytes,
        chunk_index: int,
        offset_seconds: float = 0.0,
    ) -> list[TranscriptSegment]:
        # faster-whisper butuh file path, bukan bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp_path = f.name

        try:
            segments_iter, info = self.model.transcribe(
                tmp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,        # Skip silence otomatis
                vad_parameters={"min_silence_duration_ms": 500},
            )
            segments = []
            for seg in segments_iter:
                segments.append(TranscriptSegment(
                    chunk_index=chunk_index,
                    start_time=offset_seconds + seg.start,
                    end_time=offset_seconds + seg.end,
                    text=seg.text.strip(),
                    language=info.language,
                ))
            return segments
        finally:
            os.unlink(tmp_path)
```

---

### 2.8 `TranscriptAggregator` (`ai/aggregator.py`)

```python
from ..transcription.engine import TranscriptSegment

class TranscriptAggregator:
    def __init__(self, overlap_tolerance_s: float = 1.5):
        self._segments: list[TranscriptSegment] = []
        self.overlap_tolerance = overlap_tolerance_s

    def add_segments(self, segments: list[TranscriptSegment]) -> None:
        self._segments.extend(segments)
        # Sort by start_time
        self._segments.sort(key=lambda s: s.start_time)

    def deduplicate(self) -> list[TranscriptSegment]:
        """Hapus duplikasi dari overlap chunks."""
        if not self._segments:
            return []
        
        deduped = [self._segments[0]]
        for current in self._segments[1:]:
            last = deduped[-1]
            # Jika start time terlalu dekat (dalam overlap window), skip
            if current.start_time < last.end_time - self.overlap_tolerance:
                continue
            deduped.append(current)
        return deduped

    def to_text(self) -> str:
        """Format ke plain text dengan timestamp."""
        segs = self.deduplicate()
        lines = []
        for seg in segs:
            ts = self._format_time(seg.start_time)
            lines.append(f"[{ts}] {seg.text}")
        return "\n".join(lines)

    def to_json(self) -> list[dict]:
        return [
            {
                "start": round(s.start_time, 2),
                "end": round(s.end_time, 2),
                "text": s.text,
            }
            for s in self.deduplicate()
        ]

    @staticmethod
    def _format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
```

---

### 2.9 `LLMSummarizer` (`ai/summarizer.py` dan `ai/gemini.py`)

```python
# ai/summarizer.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class MeetingSummary:
    executive_summary: str
    key_decisions: list[str]
    action_items: list[dict]    # [{task, owner, deadline}]
    topics_discussed: list[str]
    next_steps: str
    raw_markdown: str

class LLMSummarizer(ABC):
    @abstractmethod
    async def summarize(self, transcript_text: str) -> MeetingSummary:
        ...
```

```python
# ai/gemini.py
from google import genai
import json
from .summarizer import LLMSummarizer, MeetingSummary

SUMMARY_PROMPT = """Kamu adalah asisten yang ahli membuat ringkasan meeting.

Berikut adalah transcript meeting:

<transcript>
{transcript}
</transcript>

Buat ringkasan dalam format JSON dengan struktur berikut (jawab HANYA dengan JSON, tanpa markdown code block):
{{
  "executive_summary": "Ringkasan eksekutif 2-3 kalimat",
  "key_decisions": ["Keputusan 1", "Keputusan 2"],
  "action_items": [
    {{"task": "Deskripsi tugas", "owner": "Nama/tim (jika disebutkan)", "deadline": "Deadline (jika disebutkan)"}}
  ],
  "topics_discussed": ["Topik 1", "Topik 2"],
  "next_steps": "Langkah selanjutnya yang perlu dilakukan"
}}"""

class GeminiSummarizer(LLMSummarizer):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def summarize(self, transcript_text: str) -> MeetingSummary:
        # Jika transcript panjang, potong ke ~80k chars (context limit)
        max_chars = 80_000
        if len(transcript_text) > max_chars:
            transcript_text = transcript_text[:max_chars] + "\n[Transcript dipotong...]"

        prompt = SUMMARY_PROMPT.format(transcript=transcript_text)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        raw_json = response.text
        data = json.loads(raw_json)
        
        # Format ke markdown
        md = self._to_markdown(data)
        
        return MeetingSummary(
            executive_summary=data["executive_summary"],
            key_decisions=data["key_decisions"],
            action_items=data["action_items"],
            topics_discussed=data["topics_discussed"],
            next_steps=data["next_steps"],
            raw_markdown=md,
        )

    def _to_markdown(self, data: dict) -> str:
        lines = [
            "# Meeting Summary\n",
            "## Executive Summary",
            data["executive_summary"],
            "",
            "## Key Decisions",
            *[f"- {d}" for d in data["key_decisions"]],
            "",
            "## Action Items",
            "| Task | Owner | Deadline |",
            "|------|-------|----------|",
            *[f"| {a['task']} | {a.get('owner', '-')} | {a.get('deadline', '-')} |"
              for a in data["action_items"]],
            "",
            "## Topics Discussed",
            *[f"- {t}" for t in data["topics_discussed"]],
            "",
            "## Next Steps",
            data["next_steps"],
        ]
        return "\n".join(lines)
```

---

### 2.10 `OutputManager` (`output/manager.py`)

```python
import os
import json
import shutil
from datetime import datetime
from pathlib import Path

class OutputManager:
    def __init__(self, base_dir: str = "./recordings"):
        self.base_dir = Path(base_dir)
        self.session_dir: Path = None
        self._session_id: str = None

    def start_session(self) -> str:
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.base_dir / self._session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        return self._session_id

    def save_audio(self, source_path: str) -> Path:
        dest = self.session_dir / "recording.wav"
        shutil.copy2(source_path, dest)
        return dest

    def save_transcript(self, segments: list[dict]) -> dict[str, Path]:
        # JSON format
        json_path = self.session_dir / "transcript.json"
        json_path.write_text(json.dumps(segments, ensure_ascii=False, indent=2))
        
        # Plain text format
        txt_path = self.session_dir / "transcript.txt"
        lines = []
        for seg in segments:
            ts = self._format_time(seg["start"])
            lines.append(f"[{ts}] {seg['text']}")
        txt_path.write_text("\n".join(lines), encoding="utf-8")
        
        return {"json": json_path, "txt": txt_path}

    def save_summary(self, markdown_content: str) -> Path:
        path = self.session_dir / "summary.md"
        path.write_text(markdown_content, encoding="utf-8")
        return path

    @staticmethod
    def _format_time(seconds: float) -> str:
        h, r = divmod(int(seconds), 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
```

---

## 3. Konfigurasi (`config/settings.py`)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API Keys
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    # Audio
    sample_rate: int = 16000
    chunk_duration_s: float = 30.0
    overlap_s: float = 2.0
    capture_system_audio: bool = True
    capture_microphone: bool = True

    # Transcription
    transcription_backend: Literal["whisper_api", "whisper_local"] = "whisper_api"
    whisper_model_size: str = "medium"   # Untuk local
    language: str = "id"                 # Bahasa utama meeting

    # LLM
    llm_backend: Literal["gemini", "openai"] = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o"

    # Output
    output_dir: str = "./recordings"
    save_audio: bool = True
```

---

## 4. Dependency Matrix

```toml
# pyproject.toml
[project]
name = "meeting-recorder"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Audio capture
    "sounddevice>=0.4.6",
    "numpy>=1.26",
    "scipy>=1.12",

    # Transcription
    "openai>=1.30",           # Whisper API + GPT
    "faster-whisper>=1.0",    # Local transcription

    # AI Summary
    "google-genai>=1.0",

    # Config & CLI
    "pydantic-settings>=2.3",
    "click>=8.1",
    "rich>=13.7",
]

[project.optional-dependencies]
windows = [
    "pyaudiowpatch>=0.2.12",  # WASAPI Loopback
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]
```

---

## 5. Error Handling Strategy

| Error | Penyebab | Penanganan |
|---|---|---|
| `No loopback device found` | Driver tidak support WASAPI Loopback | Fallback ke mic only, tampilkan warning |
| `BlackHole not found` | BlackHole belum di-install (macOS) | Print instruksi install, exit gracefully |
| `Whisper API rate limit` | Terlalu banyak request | Exponential backoff + retry max 3x |
| `Chunk too short` | Silence panjang | Skip chunk, log warning |
| `LLM context too long` | Transcript > 100k chars | Truncate atau split transcript + summarize per-bagian |
| `Network timeout` | Koneksi bermasalah | Queue chunk, retry saat koneksi kembali |
| `Audio device disconnected` | Headset/speaker dicabut | Graceful stop + simpan hasil sementara |

---

## 6. Thread & Async Architecture

```
Main Thread
│
├── AudioCaptureEngine.start()     ← [Thread: audio-capture]
│   └── pyaudio/sounddevice callback dipanggil oleh OS
│
├── AudioChunker.start()           ← [Thread: chunker]
│   └── Loop: pop dari RingBuffer → emit chunk
│
└── asyncio Event Loop             ← [Main Thread async]
    ├── TranscriptionEngine.transcribe()  ← async, concurrent
    ├── TranscriptAggregator.add()
    └── LLMSummarizer.summarize()         ← dipanggil setelah stop
```

**Penggunaan `asyncio.Queue` untuk komunikasi antar-komponen:**
```python
# Antara chunker dan transcriber
chunk_queue: asyncio.Queue[tuple[bytes, int]] = asyncio.Queue(maxsize=10)
```
