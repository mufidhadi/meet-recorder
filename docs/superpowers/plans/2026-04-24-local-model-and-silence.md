# Local Model, Silence Detection & Incremental Save Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menambahkan opsi transkripsi model lokal, mendeteksi keheningan (silence) untuk menghemat API, dan menyimpan transkrip secara real-time.

**Architecture:** 
- `LocalHFTranscriber` menggunakan HuggingFace `pipeline`.
- `AudioChunker` menghitung RMS (Root Mean Square) energy untuk mendeteksi silence.
- CLI di-update untuk melakukan incremental save pada `OutputManager`.

**Tech Stack:** Python 3.12, transformers, torch, numpy.

---

### Task 11: Configuration Update & Incremental Save

**Files:**
- Modify: `meeting_recorder/config/settings.py`
- Modify: `meeting_recorder/cli/main.py`

- [ ] **Step 1: Update Settings**
File: `meeting_recorder/config/settings.py`
Add fields for engine selection and silence threshold:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from meeting_recorder.data.audio import AudioConfig

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    audio: AudioConfig = AudioConfig()
    
    # Engine: "gemini" or "local"
    transcription_engine: str = "gemini"
    local_model_id: str = "openai/whisper-tiny" # Fallback light model, users can set to gemma if supported
    
    gemini_api_key: str | None = None
    output_dir: str = "./recordings"
    
    # Silence detection: RMS threshold (0.0 to 1.0)
    silence_threshold: float = 0.01 
```

- [ ] **Step 2: Update CLI to save incrementally and select engine**
File: `meeting_recorder/cli/main.py`
Modify `_record_async` and `_handle_chunk`:
```python
# In _record_async setup transcriber based on config
    if settings.transcription_engine == "local":
        from meeting_recorder.transcription.local_hf import LocalHFTranscriber
        transcriber = LocalHFTranscriber(model_id=settings.local_model_id)
    else:
        transcriber = GeminiTranscriber(api_key=settings.gemini_api_key)

# In _handle_chunk, add incremental save
async def _handle_chunk(idx: int, wav_bytes: bytes, transcriber, aggregator, output_mgr):
    try:
        offset = idx * 30.0 # MVP static offset
        result = await transcriber.transcribe(wav_bytes)
        aggregator.add_result(result, offset_s=offset)
        output_mgr.save_audio_chunk(idx, wav_bytes)
        
        # Incremental Save
        full_text = aggregator.get_full_transcript()
        output_mgr.save_transcript(aggregator.all_segments, full_text)
        
        console.print(f"[dim]Chunk {idx} transcribed: {result.full_text[:50]}...[/dim]")
    except Exception as e:
        console.print(f"[red]Error transcribing chunk {idx}: {e}[/red]")
```

- [ ] **Step 3: Commit**
```bash
git add meeting_recorder/config/settings.py meeting_recorder/cli/main.py
git commit -m "feat: add config for local models and implement incremental saving"
```

---

### Task 12: Silence Detection in Chunker

**Files:**
- Modify: `meeting_recorder/processing/chunker.py`

- [ ] **Step 1: Add RMS calculation and threshold skip**
File: `meeting_recorder/processing/chunker.py`
Update `_run` method:
```python
    def _run(self):
        # We need the settings to know the threshold, or pass it in __init__
        # For simplicity, let's pass threshold to __init__
        pass 
```
*Wait, let's redefine the full class.*
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

def is_silent(data: np.ndarray, threshold: float = 0.01) -> bool:
    """Calculate RMS energy and check against threshold."""
    if len(data) == 0:
        return True
    
    # Convert to float32 for calculation to avoid overflow, normalize to -1.0 to 1.0
    float_data = data.astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(float_data**2))
    return rms < threshold

class AudioChunker:
    def __init__(self, ring_buffer, chunk_duration_s: float, on_chunk_callback: Callable[[bytes], None], silence_threshold: float = 0.01):
        self.ring_buffer = ring_buffer
        self.chunk_duration_s = chunk_duration_s
        self.on_chunk_callback = on_chunk_callback
        self.silence_threshold = silence_threshold
        self._stop_event = threading.Event()
        self._thread = None

    def _run(self):
        while not self._stop_event.is_set():
            if self.ring_buffer.available_seconds >= self.chunk_duration_s:
                data = self.ring_buffer.get_last_n_seconds(self.chunk_duration_s)
                
                # Check for silence before processing
                if not is_silent(data, self.silence_threshold):
                    wav_bytes = export_to_wav_bytes(data, self.ring_buffer.sample_rate)
                    self.on_chunk_callback(wav_bytes)
                else:
                    # Skip silence, save API calls
                    print("[dim]Chunk skipped (Silence detected)[/dim]")
                
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

- [ ] **Step 2: Update CLI to pass silence_threshold**
File: `meeting_recorder/cli/main.py`
Change chunker instantiation:
```python
    chunker = AudioChunker(
        buffer, 
        chunk_duration_s=chunk_size, 
        on_chunk_callback=on_chunk_ready,
        silence_threshold=settings.silence_threshold
    )
```

- [ ] **Step 3: Commit**
```bash
git add meeting_recorder/processing/chunker.py meeting_recorder/cli/main.py
git commit -m "feat: implement voice activity detection to skip silent chunks"
```

---

### Task 13: Local HF Transcriber

**Files:**
- Create: `meeting_recorder/transcription/local_hf.py`

- [ ] **Step 1: Install transformers and torch**
Run: `uv add transformers torch torchaudio soundfile`

- [ ] **Step 2: Implement LocalHFTranscriber**
File: `meeting_recorder/transcription/local_hf.py`
```python
import io
import soundfile as sf
import numpy as np
from transformers import pipeline
from meeting_recorder.transcription.engine import Transcriber
from meeting_recorder.data.transcription import TranscriptResult, TranscriptSegment

class LocalHFTranscriber(Transcriber):
    def __init__(self, model_id: str):
        # Initialize pipeline. Will download model on first run.
        # This pipeline works for whisper models, and some others supported by HF ASR.
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model_id,
            device="cpu" # Use "cuda" if GPU is available, keeping CPU for max compatibility
        )

    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        # Transformers pipeline usually expects a numpy array or file path
        # Convert WAV bytes to numpy array
        audio_file = io.BytesIO(audio_bytes)
        data, samplerate = sf.read(audio_file)
        
        # If stereo, convert to mono
        if len(data.shape) > 1:
            data = data.mean(axis=1)

        # Run inference synchronously (MVP: wrapped in async def for interface compatibility)
        result = self.pipe(data)
        text = result["text"].strip()
        
        return TranscriptResult(
            segments=[TranscriptSegment(start=0.0, end=30.0, text=text)],
            full_text=text
        )
```

- [ ] **Step 3: Commit**
```bash
git add meeting_recorder/transcription/local_hf.py
git commit -m "feat: add local HuggingFace transcriber support"
```
