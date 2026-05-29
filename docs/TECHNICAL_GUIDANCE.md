# Meet-Recorder: Technical Guidance

> Panduan teknis ini adalah **pelengkap** dari TDD dan Implementation Plan.  
> Isinya fokus pada keputusan teknis yang tidak obvious, gotcha di implementasi, dan pola yang harus konsisten di seluruh codebase.

---

## 1. Toolchain & Workflow

### Gunakan `uv` untuk segalanya

Proyek ini menggunakan `uv`, bukan `pip` atau `conda`.

```bash
# Tambah dependency baru
uv add google-genai

# Tambah dev dependency
uv add --dev pytest-asyncio

# Tambah optional dependency
uv add --optional windows pyaudiowpatch

# Jalankan script/command
uv run python scratch/test_capture.py
uv run pytest tests/ -v
uv run ruff check src/

# Install semua extras sekaligus (untuk dev)
uv sync --all-extras
```

**Jangan pernah:** `pip install ...` langsung. Selalu lewat `uv`.

### Struktur file yang wajib ada sebelum coding

```
src/meeting_recorder/
├── __init__.py          ← wajib, bisa kosong
├── capture/
│   └── __init__.py      ← wajib
├── processing/
│   └── __init__.py      ← wajib
├── transcription/
│   └── __init__.py      ← wajib
├── ai/
│   └── __init__.py      ← wajib
├── output/
│   └── __init__.py      ← wajib
├── detection/
│   └── __init__.py      ← wajib (Sprint 3)
└── config/
    └── __init__.py      ← wajib
```

---

## 2. Threading & Async: Aturan Besi

Ini bagian yang paling sering bikin bug. Pahami betul sebelum implementasi.

### Tiga "dunia" yang bersamaan

```
┌─────────────────────────────────────────────────────────┐
│ WORLD 1: OS Audio Thread                                 │
│ (pyaudiowpatch callback, dipanggil oleh OS, bukan kita)  │
│                                                          │
│  • DILARANG: I/O, blocking call, print()                 │
│  • BOLEH: push ke queue/buffer (non-blocking)            │
└─────────────────────────────────────────────────────────┘
          │ push(data)
          ▼
┌─────────────────────────────────────────────────────────┐
│ WORLD 2: Python Thread (AudioChunker._process_loop)      │
│                                                          │
│  • DILARANG: asyncio calls langsung (create_task, await) │
│  • BOLEH: pop dari buffer, encode WAV, call_soon_threadsafe│
└─────────────────────────────────────────────────────────┘
          │ loop.call_soon_threadsafe(...)
          ▼
┌─────────────────────────────────────────────────────────┐
│ WORLD 3: asyncio Event Loop (Main Thread)                │
│                                                          │
│  • BOLEH: await, create_task, async API calls            │
│  • DILARANG: time.sleep() — gunakan await asyncio.sleep()│
└─────────────────────────────────────────────────────────┘
```

### Pattern yang BENAR untuk chunk callback

```python
# Di main.py — ini yang benar:
loop = asyncio.get_event_loop()

def sync_chunk_callback(wav_bytes: bytes, chunk_idx: int):
    # Dipanggil dari Python Thread (World 2)
    # Gunakan call_soon_threadsafe untuk masuk ke asyncio world
    loop.call_soon_threadsafe(
        lambda: asyncio.ensure_future(handle_chunk(wav_bytes, chunk_idx))
    )

# JANGAN LAKUKAN INI (akan error):
def wrong_callback(wav_bytes, chunk_idx):
    asyncio.create_task(handle_chunk(wav_bytes, chunk_idx))  # ❌ RuntimeError
```

### Tunggu semua task transcription selesai sebelum summarize

```python
# Di _record_async() — setelah stop:
pending_tasks = [t for t in asyncio.all_tasks() 
                 if not t.done() and t != asyncio.current_task()]
if pending_tasks:
    await asyncio.gather(*pending_tasks, return_exceptions=True)

# Baru kemudian:
summary = await summarizer.summarize(aggregator.to_text())
```

---

## 3. RingBuffer: Gotcha yang Sering Dilupakan

### Maxsize harus cukup besar

Default `maxsize_seconds=60` artinya buffer bisa menampung 60 detik × 16000 samples = 960,000 samples int16 = ~1.9MB. Ini fine.

Jangan set terlalu kecil — jika chunker lambat (API transcription timeout), buffer akan overflow dan data hilang tanpa error.

### `deque(maxlen=...)` behavior

Ketika `maxlen` tercapai, elemen terlama di-pop otomatis. Ini adalah **silent data loss** — tidak ada exception. Design-wise ini acceptable karena kita lebih suka kehilangan data lama daripada crash, tapi perlu di-log:

```python
def push(self, data: np.ndarray) -\u003e None:
    with self._lock:
        before = len(self._buffer)
        self._buffer.extend(data.tolist())
        after = len(self._buffer)
        lost = (before + len(data)) - after
        if lost > 0:
            logger.warning(f"RingBuffer overflow: {lost} samples dropped")
    self._data_event.set()
```

---

## 4. WASAPI Loopback: Hal-Hal yang Tidak Ada di Dokumentasi

### Stereo vs Mono

WASAPI Loopback device bisa stereo (2 channel). `AudioConfig.channels = 1` (mono) mungkin tidak match dengan format device. Bisa menyebabkan error.

**Solusi:** Detect channel count device, capture stereo, lalu downmix ke mono:

```python
def _downmix_to_mono(self, data: np.ndarray, channels: int) -\u003e np.ndarray:
    if channels == 1:
        return data
    # Reshape dan rata-ratakan channel
    return data.reshape(-1, channels).mean(axis=1).astype(np.int16)
```

### Sample rate mismatch

Whisper butuh 16kHz. Device loopback mungkin 44.1kHz atau 48kHz. **Jangan assume 16kHz bisa langsung dipakai.**

```python
# Buka stream dengan native sample rate device
device_info = self._pa.get_device_info_by_index(loopback_idx)
native_rate = int(device_info["defaultSampleRate"])  # biasanya 44100 atau 48000

# Capture dengan native rate, lalu resample
from scipy.signal import resample_poly
import math

def _resample(self, data: np.ndarray, orig_rate: int, target_rate: int) -\u003e np.ndarray:
    gcd = math.gcd(orig_rate, target_rate)
    up = target_rate // gcd
    down = orig_rate // gcd
    return resample_poly(data, up, down).astype(np.int16)
```

### Default WASAPI Loopback Device

Metode `_find_loopback_device()` di TDD mencari nama yang *diawali* nama default speaker. Ini bisa gagal kalau nama device mengandung karakter Unicode atau trailing spaces. Tambahkan normalisasi:

```python
def _find_loopback_device(self) -\u003e int:
    wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    default_idx = wasapi_info["defaultOutputDevice"]
    speaker_name = self._pa.get_device_info_by_index(default_idx)["name"].strip()
    
    for i in range(self._pa.get_device_count()):
        info = self._pa.get_device_info_by_index(i)
        if (info.get("isLoopbackDevice") and 
            info["name"].strip().startswith(speaker_name[:20])):  # prefix match saja
            return i
    
    raise RuntimeError(
        "WASAPI Loopback device tidak ditemukan.\n"
        "Pastikan speaker default aktif dan driver mendukung WASAPI.\n"
        f"Speaker default: {speaker_name}\n"
        f"Jalankan 'meeting-recorder devices' untuk lihat semua device."
    )
```

---

## 5. Whisper API: Biaya & Optimasi

### Cara hitung chunk offset dengan benar

Chunk ke-N dimulai pada:
```python
offset = chunk_index * (chunk_duration_s - overlap_s)
# Chunk 0: offset = 0 detik
# Chunk 1: offset = 28 detik (30 - 2)
# Chunk 2: offset = 56 detik
```

**Jangan** pakai `chunk_index * chunk_duration_s` karena akan salah hitung karena overlap.

### Prompt untuk akurasi bahasa Indonesia

Whisper API bisa "dikasih tahu" konteks via prompt parameter. Ini sangat efektif untuk nama orang dan istilah teknis:

```python
# Di Settings, tambahkan field:
whisper_prompt: str = ""  # User bisa set via .env

# Di WhisperAPITranscriber:
response = await self.client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    language="id",
    prompt=settings.whisper_prompt or "Meeting bisnis dalam Bahasa Indonesia.",
    response_format="verbose_json",
    timestamp_granularities=["segment"],
)
```

### Retry dengan exponential backoff

```python
import asyncio
import logging

async def _transcribe_with_retry(self, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await self._do_transcribe(*args, **kwargs)
        except openai.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # 1, 2, 4 detik
            logging.warning(f"Rate limit, retry in {wait}s (attempt {attempt+1}/{max_retries})")
            await asyncio.sleep(wait)
        except openai.APITimeoutError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
```

---

## 6. LLM Summarizer: Parsing JSON yang Robust

Gemini kadang menambahkan penjelasan teks di luar JSON meski sudah diminta tidak. Gunakan regex untuk ekstrak JSON:

```python
import re
import json

def _parse_response(self, raw_text: str) -\u003e dict:
    # Coba langsung parse dulu
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass
    
    # Cari JSON block dalam teks
    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Fallback: return partial summary
    logging.error(f"Failed to parse LLM response: {raw_text[:200]}")
    return {
        "executive_summary": "Gagal parse response LLM.",
        "key_decisions": [],
        "action_items": [],
        "topics_discussed": [],
        "next_steps": raw_text[:500],
    }
```

---

## 7. Pola Logging yang Konsisten

Gunakan `logging` standar Python, bukan `print()` di production code:

```python
# Di setiap module:
import logging
logger = logging.getLogger(__name__)

# Gunakan level yang tepat:
logger.debug(f"Buffer size: {len(buffer)}")         # Untuk debugging
logger.info("Recording started")                     # Normal operations
logger.warning(f"Chunk {idx} took {t:.1f}s")        # Degraded performance
logger.error(f"Transcription failed: {e}")           # Error tapi tidak fatal
logger.critical("Audio device disconnected")         # Fatal
```

Setup logging di `main.py`:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),                      # Console
        logging.FileHandler("meeting_recorder.log"),  # File
    ]
)
```

---

## 8. Struktur Test yang Diharapkan

### Konvensi penamaan

```python
# tests/unit/test_chunker.py

def test_overlap_data_carried_forward():
    """Pastikan 2 detik terakhir chunk N menjadi awal chunk N+1."""
    ...

def test_wav_bytes_valid_format():
    """WAV bytes yang dihasilkan bisa dibaca library wave standar."""
    ...

def test_stop_join_timeout():
    """stop() tidak hang meski thread lambat."""
    ...
```

### Mock untuk komponen eksternal

```python
# Untuk API calls — gunakan mock, jangan panggil API sungguhan di test
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_whisper_retry_on_rate_limit():
    with patch("openai.AsyncOpenAI") as mock_client:
        mock_client.return_value.audio.transcriptions.create.side_effect = [
            openai.RateLimitError("rate limit", response=None, body=None),
            openai.RateLimitError("rate limit", response=None, body=None),
            MagicMock(segments=[]),  # Sukses di attempt ke-3
        ]
        transcriber = WhisperAPITranscriber(api_key="test")
        result = await transcriber.transcribe(b"fake_wav", 0)
        assert result == []
```

### File audio sintetis untuk test

```python
# Buat WAV 1 detik silence untuk test — jangan commit file binary
def make_silent_wav(duration_s: float = 1.0, sample_rate: int = 16000) -\u003e bytes:
    import numpy as np, io, wave
    samples = np.zeros(int(duration_s * sample_rate), dtype=np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()
```

---

## 9. Keputusan Desain yang Sudah Final (Jangan Diubah Tanpa Diskusi)

| Keputusan | Alasan |
|-----------|--------|
| `uv` sebagai package manager | Konsistensi, speed, lockfile deterministik |
| `int16` sebagai dtype audio (bukan `float32`) | Kompatibel dengan pyaudiowpatch; Whisper API butuh format ini |
| 30 detik chunk, 2 detik overlap | Sudah divalidasi di desain; overlap cukup untuk kata yang terpotong |
| `asyncio.Queue` antara chunker dan transcriber | Backpressure control; transcription bisa lebih lambat dari capture |
| `pydantic-settings` bukan `dynaconf` | Type safety, sudah familiar, `.env` support bawaan |
| Output direktori per-session (`YYYYMMDD_HHMMSS`) | Tidak ada collision, mudah di-sort, mudah di-delete |
| Gemini sebagai default LLM | Kualitas summary sangat baik untuk Bahasa Indonesia, biaya lebih rendah dari alternatif lain |

---

## 10. File `.gitignore` yang Perlu Ditambahkan

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
dist/
*.egg-info/

# Environment
.env
*.env.local

# Output recordings (jangan commit audio/transcript)
recordings/
*.wav
*.mp3

# Logs
*.log
meeting_recorder.log

# Models (faster-whisper akan download model)
models/

# Scratch/temp
scratch/

# OS
.DS_Store
Thumbs.db
```

---

## Referensi Cepat

| Komponen | File | Dokumentasi |
|----------|------|-------------|
| AudioCaptureEngine (ABC) | `capture/engine.py` | TDD §2.1 |
| WindowsCaptureEngine | `capture/windows.py` | TDD §2.2 |
| RingBuffer | `processing/buffer.py` | TDD §2.5 |
| AudioChunker | `processing/chunker.py` | TDD §2.6 |
| WhisperAPITranscriber | `transcription/whisper_api.py` | TDD §2.7 |
| WhisperLocalTranscriber | `transcription/whisper_local.py` | TDD §2.7 |
| TranscriptAggregator | `ai/aggregator.py` | TDD §2.8 |
| GeminiSummarizer | `ai/gemini.py` | TDD §2.9 |
| OutputManager | `output/manager.py` | TDD §2.10 |
| Settings | `config/settings.py` | TDD §3 |
| MeetingDetector | `detection/meeting_detector.py` | Meeting Detection §3 |
| CLI main | `main.py` | Implementation Guide §4 |
