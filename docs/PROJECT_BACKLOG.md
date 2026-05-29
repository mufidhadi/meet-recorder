# Meet-Recorder: Project Backlog

> **Status:** Planning → Implementation  
> **Tanggal dibuat:** April 2026  
> **Target awal:** MVP v0.1 (Windows, Whisper API, Gemini)

---

## Ringkasan Scope

Sistem ini merekam audio meeting dari level OS (tanpa SDK platform), mentranskripsikan dengan Whisper, dan menghasilkan summary terstruktur via LLM. Arsitektur sudah terdefinisi di `docs/plan_and_design/`. Tugas kita sekarang adalah **membangun implementasinya dari nol**.

---

## Epic Breakdown

| Epic | Kode | Deskripsi | Sprint |
|------|------|-----------|--------|
| Fondasi Proyek | EP-01 | Setup struktur, config, tooling | Sprint 1 |
| Audio Capture | EP-02 | AudioCaptureEngine cross-platform | Sprint 1 |
| Audio Processing | EP-03 | Buffer, chunker, VAD | Sprint 1 |
| Transcription | EP-04 | Whisper API & local backend | Sprint 2 |
| AI Pipeline | EP-05 | Aggregator + LLM Summarizer | Sprint 2 |
| Output Management | EP-06 | File saving, formatting | Sprint 2 |
| CLI & UX | EP-07 | Click CLI + Rich display | Sprint 2 |
| Auto-Detection | EP-08 | Meeting detector (4-signal system) | Sprint 3 |
| Testing | EP-09 | Unit & integration tests | Sprint 3 |
| Polish & Docs | EP-10 | Error handling, README, packaging | Sprint 3 |

---

## EP-01: Fondasi Proyek

### EP-01-T01 — Inisialisasi struktur direktori proyek
- **Aksi:** Buat semua folder dan file `__init__.py` sesuai TDD §1
- **Deliverable:** Direktori `src/meeting_recorder/` dengan sub-paket `capture`, `processing`, `transcription`, `ai`, `output`, `config`
- **Acceptance Criteria:** `uv run python -c "import meeting_recorder"` tidak error

### EP-01-T02 — Setup pyproject.toml lengkap
- **Aksi:** Isi `pyproject.toml` dengan semua dependency dari TDD §4 (Dependency Matrix)
- **Dependencies core:** `sounddevice`, `numpy`, `scipy`, `openai`, `faster-whisper`, `google-genai`, `pydantic-settings`, `click`, `rich`
- **Optional groups:** `windows` (pyaudiowpatch), `detection` (psutil, pywin32), `dev` (pytest, ruff)
- **Acceptance Criteria:** `uv sync` berhasil, `uv sync --extra windows` berhasil di Windows

### EP-01-T03 — Setup konfigurasi pydantic-settings
- **Aksi:** Implementasi `src/meeting_recorder/config/settings.py` sesuai TDD §3
- **Fields:** API keys, audio params, transcription backend, LLM backend, output dir
- **Deliverable:** `.env.example` template + `Settings` class
- **Acceptance Criteria:** `Settings()` bisa di-load dari environment variable dan file `.env`

### EP-01-T04 — Setup tooling: ruff, pytest, uv scripts
- **Aksi:** Tambahkan `[tool.ruff]`, `[tool.pytest.ini_options]`, dan `[project.scripts]` ke `pyproject.toml`
- **Entry point:** `meeting-recorder = "meeting_recorder.main:cli"`
- **Acceptance Criteria:** `uv run ruff check .` jalan, `uv run pytest` jalan (meski 0 test)

---

## EP-02: Audio Capture Engine

### EP-02-T01 — Implementasi abstract base class AudioCaptureEngine
- **Aksi:** Buat `capture/engine.py` dengan `AudioConfig` dataclass dan `AudioCaptureEngine` ABC
- **Implementasi:** `list_devices()`, `start()`, `stop()`, property `is_recording`
- **Platform factory:** Fungsi `create_capture_engine()` yang dispatch berdasarkan `platform.system()`
- **Ref dokumen:** TDD §2.1
- **Acceptance Criteria:** Import berjalan, factory function raise `NotImplementedError` untuk platform unknown

### EP-02-T02 — Implementasi Windows WASAPI Loopback
- **Aksi:** Buat `capture/windows.py` — `WindowsCaptureEngine`
- **Detail implementasi:**
  - Auto-detect loopback device via `_find_loopback_device()`
  - Mix system audio + mic via callback double-buffer
  - Normalize float32, clip, convert kembali ke int16
- **Library:** `pyaudiowpatch`
- **Ref dokumen:** TDD §2.2
- **Acceptance Criteria:** `engine.list_devices()` menampilkan loopback device; `engine.start()` → `engine.stop()` tidak raise exception di Windows 10/11

### EP-02-T03 — Implementasi macOS BlackHole
- **Aksi:** Buat `capture/macos.py` — `MacOSCaptureEngine`
- **Detail:** Auto-detect BlackHole device by name, capture mono via `sounddevice.InputStream`
- **Ref dokumen:** TDD §2.3
- **Acceptance Criteria:** Berhasil capture di macOS dengan BlackHole terinstall; error informatif jika BlackHole tidak ada

### EP-02-T04 — Implementasi Linux PulseAudio Monitor
- **Aksi:** Buat `capture/linux.py` — `LinuxCaptureEngine`
- **Detail:** Auto-detect monitor source via `pactl get-default-sink`, capture via `sounddevice`
- **Ref dokumen:** TDD §2.4
- **Acceptance Criteria:** Berhasil capture di Ubuntu 22.04+ dengan PulseAudio/PipeWire

---

## EP-03: Audio Processing

### EP-03-T01 — Implementasi RingBuffer thread-safe
- **Aksi:** Buat `processing/buffer.py` — `RingBuffer`
- **Detail:**
  - `push(data: np.ndarray)` — thread-safe via lock + event
  - `pop(n_samples, timeout)` — blocking wait dengan event
  - `deque(maxlen=...)` sebagai underlying storage
- **Ref dokumen:** TDD §2.5
- **Acceptance Criteria:** Push dari thread-1, pop dari thread-2 tanpa race condition; timeout berfungsi benar

### EP-03-T02 — Implementasi AudioChunker dengan overlap
- **Aksi:** Buat `processing/chunker.py` — `AudioChunker`
- **Detail:**
  - Berjalan di thread terpisah, loop `pop()` dari RingBuffer
  - Accumulate overlap dari chunk sebelumnya
  - Encode ke WAV bytes via `wave` module
  - Callback `on_chunk(wav_bytes, chunk_index)`
- **Ref dokumen:** TDD §2.6
- **Acceptance Criteria:** 10 detik audio menghasilkan minimal 1 chunk; chunk berikutnya mengandung 2 detik data dari chunk sebelumnya

### EP-03-T03 — Implementasi VAD (Voice Activity Detection) — opsional
- **Aksi:** Buat `processing/vad.py` — wrapper sederhana di atas WebRTC VAD atau `silero-vad`
- **Detail:** Filter silence frames sebelum dimasukkan ke chunker; hemat API cost 20-40%
- **Priority:** LOW — bisa defer ke v0.2
- **Acceptance Criteria:** VAD bisa di-enable/disable via config

---

## EP-04: Transcription Engine

### EP-04-T01 — Implementasi abstract TranscriptionEngine + TranscriptSegment
- **Aksi:** Buat `transcription/engine.py` — ABC + dataclass
- **Fields TranscriptSegment:** `chunk_index`, `start_time`, `end_time`, `text`, `confidence`, `language`
- **Ref dokumen:** TDD §2.7
- **Acceptance Criteria:** Import clean, dapat di-mock di test

### EP-04-T02 — Implementasi Whisper API transcriber
- **Aksi:** Buat `transcription/whisper_api.py` — `WhisperAPITranscriber`
- **Detail:**
  - `AsyncOpenAI` client
  - Request `verbose_json` dengan `timestamp_granularities=["segment"]`
  - Map response ke list `TranscriptSegment` dengan offset waktu yang benar
  - Exponential backoff untuk rate limit (max 3 retry)
- **Ref dokumen:** TDD §2.7
- **Acceptance Criteria:** Kirim WAV bytes, terima list segment bertimestamp; retry otomatis saat 429

### EP-04-T03 — Implementasi faster-whisper local transcriber
- **Aksi:** Buat `transcription/whisper_local.py` — `WhisperLocalTranscriber`
- **Detail:**
  - `WhisperModel` dengan lazy load (model di-cache)
  - Tulis WAV bytes ke tempfile, transcribe, cleanup
  - `vad_filter=True` bawaan faster-whisper
  - Async wrapper via `asyncio.to_thread()`
- **Ref dokumen:** TDD §2.7
- **Acceptance Criteria:** Model medium berhasil transcribe WAV file; tempfile dibersihkan setelah selesai

---

## EP-05: AI Pipeline

### EP-05-T01 — Implementasi TranscriptAggregator
- **Aksi:** Buat `ai/aggregator.py` — `TranscriptAggregator`
- **Detail:**
  - `add_segments()` + sort by start_time
  - `deduplicate()` — skip segment yang `start_time < last.end_time - tolerance`
  - `to_text()` — format `[HH:MM:SS] text`
  - `to_json()` — list dict `{start, end, text}`
- **Ref dokumen:** TDD §2.8
- **Acceptance Criteria:** Test deduplication: 4 segments dengan overlap → 3 hasil setelah dedup

### EP-05-T02 — Implementasi abstract LLMSummarizer + MeetingSummary
- **Aksi:** Buat `ai/summarizer.py` — ABC + dataclass
- **Fields MeetingSummary:** `executive_summary`, `key_decisions`, `action_items`, `topics_discussed`, `next_steps`, `raw_markdown`
- **Ref dokumen:** TDD §2.9

### EP-05-T03 — Implementasi GeminiSummarizer
- **Aksi:** Buat `ai/gemini.py` — `GeminiSummarizer`
- **Detail:**
  - `google.genai.Client` dengan `client.aio.models.generate_content()` untuk async
  - Model default: `gemini-2.5-flash`
  - Prompt JSON-structured output (tidak markdown code block)
  - Truncate transcript > 80k chars
  - Parse JSON response → `MeetingSummary`
  - Format markdown output via `_to_markdown()`
- **Library:** `google-genai`
- **Ref dokumen:** TDD §2.9
- **Acceptance Criteria:** Panggil Gemini API dengan transcript dummy, return `MeetingSummary` yang valid

### EP-05-T04 — Implementasi OpenAISummarizer
- **Aksi:** Buat `ai/openai_llm.py` — `OpenAISummarizer`
- **Detail:** Sama seperti Gemini tapi gunakan `AsyncOpenAI` dengan model GPT-4o
- **Acceptance Criteria:** Interchangeable dengan `GeminiSummarizer` via setting `LLM_BACKEND=openai`

---

## EP-06: Output Management

### EP-06-T01 — Implementasi OutputManager
- **Aksi:** Buat `output/manager.py` — `OutputManager`
- **Detail:**
  - `start_session()` — buat direktori `./recordings/YYYYMMDD_HHMMSS/`
  - `save_audio(source_path)` — copy WAV ke session dir
  - `save_transcript(segments)` — tulis `.json` dan `.txt`
  - `save_summary(markdown)` — tulis `.md`
- **Ref dokumen:** TDD §2.10
- **Acceptance Criteria:** Setelah recording session selesai, 4 file tersedia di direktori yang benar

---

## EP-07: CLI & UX

### EP-07-T01 — Implementasi CLI entry point
- **Aksi:** Buat `src/meeting_recorder/main.py` — Click CLI
- **Commands:**
  - `devices` — tampilkan audio device table (Rich)
  - `record` — jalankan pipeline recording (mode hybrid)
  - `transcribe <file>` — transcribe file audio yang sudah ada
  - `summarize <file>` — buat summary dari transcript file
- **Ref dokumen:** Implementation Guide §4
- **Acceptance Criteria:** `meeting-recorder --help` menampilkan semua command

### EP-07-T02 — Implementasi real-time display dengan Rich
- **Aksi:** Tambahkan live display ke `record` command
- **Detail:**
  - Header panel: backend, output dir, status
  - Live ticker: elapsed time, chunks processed, segments count
  - Stream transcript ke terminal saat diterima
  - Summary preview setelah stop
- **Ref dokumen:** Implementation Guide §3 (Flow Interaktif)
- **Acceptance Criteria:** Display tidak flickering; semua info terupdate setiap detik

### EP-07-T03 — Implementasi asyncio orchestration di record command
- **Aksi:** Hubungkan semua komponen di `_record_async()`
- **Detail:**
  - `asyncio.Queue` antara chunker dan transcriber
  - Signal handler untuk Ctrl+C (SIGINT)
  - Wait for pending transcription tasks sebelum generate summary
- **Ref dokumen:** TDD §6 (Thread & Async Architecture)
- **Acceptance Criteria:** Ctrl+C menghentikan rekaman dengan graceful; tidak ada task yang terpotong

---

## EP-08: Auto-Detection (Meeting Detector)

### EP-08-T01 — Implementasi ProcessDetector
- **Aksi:** Buat `detection/process_detector.py`
- **Detail:** Cek process list via `psutil`, bandingkan dengan `MEETING_PROCESSES` dict
- **Ref dokumen:** Meeting Detection §2.1
- **Acceptance Criteria:** Detect Zoom/Teams jika proses berjalan; return empty list jika tidak ada

### EP-08-T02 — Implementasi WindowDetector cross-platform
- **Aksi:** Buat `detection/window_detector.py`
- **Detail:**
  - Windows: `win32gui.EnumWindows`
  - macOS: AppleScript via subprocess
  - Linux: `wmctrl -l` via subprocess
- **Ref dokumen:** Meeting Detection §2.2
- **Acceptance Criteria:** Detect "Zoom Meeting" window title di masing-masing platform

### EP-08-T03 — Implementasi NetworkDetector
- **Aksi:** Buat `detection/network_detector.py`
- **Detail:** Cek active connections via `psutil.net_connections()`, bandingkan port dengan `MEETING_NETWORK_SIGNATURES`
- **Ref dokumen:** Meeting Detection §2.3
- **Acceptance Criteria:** Detect port Zoom (8801) atau Google Meet (19302) saat meeting aktif

### EP-08-T04 — Implementasi AudioAnalyzer (speech vs music)
- **Aksi:** Buat `detection/audio_analyzer.py`
- **Detail:**
  - Speech energy ratio (300Hz-3.5kHz via Welch PSD)
  - Silence ratio (RMS threshold per frame)
  - Spectral flatness (Wiener entropy)
  - Zero-crossing rate
  - Rhythm detection via RMS autocorrelation
- **Ref dokumen:** Meeting Detection §2.4
- **Acceptance Criteria:** Speech sample score > 7; musik sample score < 4

### EP-08-T05 — Implementasi MeetingDetector (sistem scoring terintegrasi)
- **Aksi:** Buat `detection/meeting_detector.py`
- **Detail:**
  - State machine: `NO_MEETING → LIKELY → IN_MEETING → UNCERTAIN`
  - Threshold: start ≥ 50, stop < 20
  - Grace period 60 detik sebelum stop
  - Callback `on_meeting_start` dan `on_meeting_end`
  - Poll loop setiap 5 detik di background thread
- **Ref dokumen:** Meeting Detection §3
- **Acceptance Criteria:** State transition benar di 9 skenario dari tabel §5

### EP-08-T06 — Integrasi MeetingDetector ke CLI command `watch`
- **Aksi:** Tambahkan command `watch` ke CLI
- **Detail:** Mode auto-detect — mulai rekam saat IN_MEETING, stop dan summarize saat NO_MEETING
- **Ref dokumen:** Meeting Detection §4
- **Acceptance Criteria:** `meeting-recorder watch` mulai rekam otomatis saat Zoom meeting dimulai

---

## EP-09: Testing

### EP-09-T01 — Unit test: RingBuffer
- **Coverage:** push/pop single thread, push/pop multi-thread, timeout behavior, maxsize eviction
- **Ref dokumen:** Implementation Guide §5

### EP-09-T02 — Unit test: AudioChunker
- **Coverage:** overlap carry-forward, correct WAV bytes output, stop/start lifecycle

### EP-09-T03 — Unit test: TranscriptAggregator
- **Coverage:** deduplication logic, to_text format, to_json format, empty input handling

### EP-09-T04 — Unit test: AudioAnalyzer
- **Coverage:** speech sample → high score, sine wave (musik) → low score, silence → low score

### EP-09-T05 — Unit test: MeetingDetector state machine
- **Coverage:** semua transition state, grace period behavior, callback firing

### EP-09-T06 — Integration test: Pipeline end-to-end dengan mock
- **Coverage:** Audio chunk → transcribe (mocked) → aggregate → summarize (mocked) → save output
- **Ref dokumen:** Implementation Guide §5

---

## EP-10: Polish & Packaging

### EP-10-T01 — Error handling komprehensif
- **Coverage:** Semua error case di TDD §5 (Error Handling Strategy)
- **Detail:** Retry logic untuk API, graceful fallback, user-friendly error messages

### EP-10-T02 — Tulis README.md
- **Detail:** Quick start, prerequisites per platform, CLI usage, cost estimation, known issues
- **Ref dokumen:** Implementation Guide §7 (Known Issues) dan §6 (Tips)

### EP-10-T03 — Setup GitHub Actions CI
- **Detail:** `uv sync`, `ruff check`, `pytest` di push/PR
- **Matrix:** Python 3.12 saja (cukup untuk v0.1)

### EP-10-T04 — Buat .env.example dan config.yaml template
- **Detail:** Dokumentasikan semua environment variable yang ada di `Settings`
- **Acceptance Criteria:** User bisa setup dari `cp .env.example .env` + edit 2 baris
