# Meet-Recorder: Implementation Plan

> **Versi:** 1.0  
> **Tanggal:** April 2026  
> **Target:** MVP v0.1 bisa rekam + transcribe + summarize di Windows

---

## Filosofi Implementasi

Proyek ini punya dokumentasi desain yang sudah sangat matang. Artinya risiko utama bukan di arsitektur, tapi di **integrasi antar komponen** dan **perilaku OS-level** (WASAPI, audio callback threading, asyncio mixing). 

Urutan build mengikuti **dependency graph**, bukan fitur yang paling kelihatan. Fondasi yang kuat sebelum integrasi.

---

## Fase 0 — Environment Setup (1-2 jam, hari pertama)

Sebelum nulis satu baris kode pun, environment harus siap.

```bash
# Verifikasi uv terinstall
uv --version

# Buat virtualenv dan sync dependencies
cd d:/project/mufid/meet-recorder
uv python pin 3.12
uv sync

# Install Windows extras
uv sync --extra windows --extra detection

# Verifikasi import dasar
uv run python -c "import sounddevice; print(sounddevice.query_devices())"
uv run python -c "import pyaudiowpatch; print('WASAPI OK')"
```

**Checkpoint:** Semua import tidak error. Daftar audio device muncul.

---

## Sprint 1 — Core Audio Pipeline (Estimasi: 3-4 hari)

**Goal Sprint 1:** Bisa merekam audio dari WASAPI dan menyimpannya ke file WAV.  
Belum perlu transcription, belum perlu UI. Pure audio pipeline.

### Hari 1: Fondasi

**Pagi:**
1. `EP-01-T01` — Buat semua direktori dan `__init__.py`
2. `EP-01-T02` — Isi `pyproject.toml` lengkap
3. `EP-01-T03` — Implementasi `config/settings.py`

**Siang:**
4. `EP-01-T04` — Setup ruff + pytest scripts
5. `EP-02-T01` — Implementasi `capture/engine.py` (ABC + factory)

**Checkpoint akhir hari 1:**
```bash
uv run python -c "from meeting_recorder.config.settings import Settings; s = Settings(); print(s)"
uv run python -c "from meeting_recorder.capture.engine import AudioConfig; print(AudioConfig())"
```

### Hari 2: Windows Audio Capture

**Satu fokus:** Implementasi `capture/windows.py` dengan teliti.

Ini bagian paling tricky — callback dari pyaudiowpatch berjalan di OS thread, bukan Python thread. Ada dua stream (system + mic) yang perlu di-mix dengan benar.

**Urutan implementasi:**
1. `list_devices()` dulu — verifikasi loopback device terdeteksi
2. `_find_loopback_device()` — auto-detect dari default output
3. Single-stream dulu (system audio only) — pastikan callback jalan
4. Tambahkan microphone stream + mixing logic
5. Test manual: rekam 10 detik, simpan ke file, dengarkan hasilnya

```python
# Test script cepat di scratch/test_capture.py
import numpy as np
import wave
from meeting_recorder.capture.engine import AudioConfig, create_capture_engine

recorded = []

def callback(data: np.ndarray):
    recorded.append(data.copy())

config = AudioConfig(capture_microphone=False)  # System audio only dulu
engine = create_capture_engine(config, callback)
engine.start()

import time
time.sleep(10)  # Rekam 10 detik

engine.stop()

# Simpan ke WAV
all_audio = np.concatenate(recorded)
with wave.open("test_capture.wav", "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(all_audio.tobytes())

print(f"Recorded {len(all_audio)/16000:.1f} seconds")
```

**Checkpoint akhir hari 2:** File `test_capture.wav` bisa didengar dengan jelas.

### Hari 3: Audio Processing (Buffer + Chunker)

**Pagi:**
1. `EP-03-T01` — Implementasi `processing/buffer.py`

**Siang:**
2. `EP-03-T02` — Implementasi `processing/chunker.py`

**Tes integrasi buffer + chunker:**
```python
# scratch/test_chunker.py
import numpy as np
from meeting_recorder.processing.buffer import RingBuffer
from meeting_recorder.processing.chunker import AudioChunker

buf = RingBuffer(maxsize_seconds=60, sample_rate=16000)
chunks_received = []

chunker = AudioChunker(
    ring_buffer=buf,
    sample_rate=16000,
    chunk_duration_s=5.0,
    overlap_s=1.0,
    on_chunk=lambda wav, idx: chunks_received.append((idx, len(wav)))
)

# Simulasi 10 detik audio
buf.push(np.zeros(160_000, dtype=np.int16))
chunker.start()

import time; time.sleep(3)
chunker.stop()

print(f"Got {len(chunks_received)} chunks: {chunks_received}")
```

**Checkpoint akhir hari 3:** Buffer + chunker berjalan di thread terpisah tanpa race condition.

### Hari 4: Integrasi Capture → Buffer → Chunker

Hubungkan `WindowsCaptureEngine` → `RingBuffer` → `AudioChunker` dalam satu pipeline.

```python
# scratch/test_pipeline_capture.py
# Rekam 30 detik, pastikan chunker menghasilkan chunk WAV yang valid
```

**Checkpoint akhir Sprint 1:** Pipeline capture-to-chunk berjalan. Bisa rekam audio meeting dan menghasilkan potongan WAV 30 detik.

---

## Sprint 2 — Transcription + AI + CLI (Estimasi: 4-5 hari)

**Goal Sprint 2:** Pipeline lengkap — dari audio capture hingga file summary tersimpan, dengan CLI yang bisa dijalankan.

### Hari 5: Transcription Layer

**Pagi:**
1. `EP-04-T01` — `transcription/engine.py` (ABC + dataclass)
2. `EP-04-T02` — `transcription/whisper_api.py`

Test Whisper API dengan file WAV dari Sprint 1:
```bash
# Set .env dulu
echo "OPENAI_API_KEY=sk-..." > .env

# Test manual
uv run python scratch/test_whisper.py
```

**Siang:**
3. `EP-04-T03` — `transcription/whisper_local.py`

**Checkpoint:** Kirim chunk WAV → terima list `TranscriptSegment` dengan timestamp.

### Hari 6: AI Pipeline (Aggregator + Summarizer)

1. `EP-05-T01` — `ai/aggregator.py`
2. `EP-05-T02` — `ai/summarizer.py` (ABC)
3. `EP-05-T03` — `ai/gemini.py`
4. `EP-05-T04` — `ai/openai_llm.py`

Test dengan transcript dummy:
```python
# scratch/test_summarizer.py
import asyncio
from meeting_recorder.ai.gemini import GeminiSummarizer

async def main():
    summarizer = GeminiSummarizer(api_key="AIza...")
    transcript = """
[00:00:04] Oke, agenda hari ini ada tiga poin.
[00:00:18] Yang pertama soal timeline Q3.
[00:00:45] Kita putuskan, deadline vendor paling lambat Jumat.
"""
    summary = await summarizer.summarize(transcript)
    print(summary.raw_markdown)

asyncio.run(main())
```

**Checkpoint:** Summary terstruktur (JSON + Markdown) berhasil digenerate.

### Hari 7: Output Manager

1. `EP-06-T01` — `output/manager.py`

Test:
```python
# scratch/test_output.py
from meeting_recorder.output.manager import OutputManager

mgr = OutputManager("./test_recordings")
session = mgr.start_session()
mgr.save_transcript([{"start": 0.0, "end": 5.0, "text": "Halo semua"}])
mgr.save_summary("# Summary\n\nTest summary.")
print(f"Session: {mgr.session_dir}")
```

**Checkpoint:** 3 file tersimpan di direktori session yang benar.

### Hari 8-9: CLI & Asyncio Orchestration

Ini bagian paling kompleks — menyambungkan semua komponen dalam satu asyncio event loop yang berjalan bersamaan dengan thread OS untuk audio.

1. `EP-07-T01` — Skeleton CLI (commands: devices, record, transcribe, summarize)
2. `EP-07-T03` — Asyncio orchestration di `_record_async()`
3. `EP-07-T02` — Rich display (opsional, bisa setelah fungsional dulu)

**Urutan implementasi `_record_async()`:**
```
1. Setup komponen (transcriber, aggregator, output_mgr, buffer, chunker)
2. Define audio_callback → push ke ring buffer
3. Define sync_chunk_callback → asyncio.create_task(handle_chunk(...))
4. Start capture_engine + chunker
5. Setup stop_event + SIGINT handler
6. Wait for stop
7. Stop capture + chunker
8. Wait for pending transcription tasks (asyncio.gather)
9. Generate summary
10. Save all outputs
```

**Checkpoint akhir Sprint 2:**
```bash
meeting-recorder devices        # Tampilkan device list
meeting-recorder record         # Rekam meeting, Ctrl+C stop, summary tersimpan
```

---

## Sprint 3 — Detection + Testing + Polish (Estimasi: 3-4 hari)

**Goal Sprint 3:** Auto-detection meeting, test coverage solid, siap dipakai.

### Hari 10-11: Meeting Auto-Detection

Bangun sistem deteksi 4-sinyal secara bertahap:

1. `EP-08-T01` — ProcessDetector (paling mudah, mulai sini)
2. `EP-08-T03` — NetworkDetector (medium)
3. `EP-08-T02` — WindowDetector (platform-specific, butuh win32gui di Windows)
4. `EP-08-T04` — AudioAnalyzer (paling complex, scipy DSP)
5. `EP-08-T05` — MeetingDetector (integrasikan semua)
6. `EP-08-T06` — CLI command `watch`

Test manual:
```bash
# Buka Zoom, mulai meeting, lalu:
meeting-recorder status
# Process: 40 (Zoom)
# Window:  35 (Zoom Meeting)
# Network: 25 (port 8801)
# Audio:    8 (speech-like)
# Total:  108 → IN_MEETING ✅
```

### Hari 12: Testing

1. `EP-09-T01` — Unit test RingBuffer
2. `EP-09-T02` — Unit test AudioChunker  
3. `EP-09-T03` — Unit test TranscriptAggregator
4. `EP-09-T04` — Unit test AudioAnalyzer
5. `EP-09-T05` — Unit test MeetingDetector state machine
6. `EP-09-T06` — Integration test dengan mock

```bash
uv run pytest tests/ -v --tb=short
```

**Target coverage:** Minimal 70% untuk logic kritis (aggregator, chunker, state machine).

### Hari 13: Polish

1. `EP-10-T01` — Error handling komprehensif (lihat TDD §5)
2. `EP-10-T02` — README.md yang layak
3. `EP-10-T04` — `.env.example` final
4. `EP-10-T03` — GitHub Actions CI (opsional)

---

## Checklist MVP v0.1

```
[ ] uv sync berjalan tanpa error
[ ] meeting-recorder devices — tampilkan WASAPI loopback device  
[ ] meeting-recorder record — rekam, transcribe, summarize
[ ] Output tersimpan di ./recordings/YYYYMMDD_HHMMSS/
[ ] 4 file: recording.wav, transcript.json, transcript.txt, summary.md
[ ] Ctrl+C graceful stop
[ ] .env.example tersedia
[ ] README ada quick start
[ ] pytest minimal jalan (tidak harus 100% pass)
```

---

## Risiko & Mitigasi

| Risiko | Kemungkinan | Dampak | Mitigasi |
|--------|-------------|--------|----------|
| WASAPI loopback tidak terdeteksi (driver issue) | Medium | Tinggi | Fallback ke mic-only mode; log instruksi troubleshoot |
| Asyncio + threading deadlock di chunk callback | Medium | Tinggi | Test isolation: uji buffer + chunker terpisah sebelum integrasi |
| Whisper API rate limit saat meeting panjang | Low | Medium | Exponential backoff sudah di desain; pastikan implementasi benar |
| faster-whisper model terlalu besar untuk RAM | Low | Low | Default ke `medium`; beri opsi `--model tiny` di CLI |
| Gemini API JSON parsing error | Low | Medium | Tambahkan fallback `json.loads` dengan error handling + retry |

---

## Dependency Build Order (Visualisasi)

```
Settings (config)
    │
    ├──► AudioConfig
    │        │
    │        ├──► WindowsCaptureEngine ──► RingBuffer ──► AudioChunker
    │        │                                                   │
    │        └──► [macos/linux engines]                          │
    │                                                            ▼
    ├──► WhisperAPITranscriber ◄─────────────── chunk (WAV bytes)
    │        │
    │        ▼
    │   TranscriptSegment[]
    │        │
    ├──► TranscriptAggregator ──► full transcript text
    │                                      │
    ├──► GeminiSummarizer ◄────────────────┘
    │        │
    │        ▼
    │   MeetingSummary
    │        │
    └──► OutputManager ──► /recordings/SESSION/
                               ├── recording.wav
                               ├── transcript.json
                               ├── transcript.txt
                               └── summary.md
```

**Rule:** Jangan pernah integrasi dua komponen yang belum punya unit test masing-masing.
