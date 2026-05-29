# Meet-Recorder: Sprint TODO

> Checklist kerja harian. Update status setiap hari.  
> Format: `[ ]` = belum, `[~]` = in progress, `[x]` = selesai

---

## Sprint 1 — Core Audio Pipeline

### Fase 0: Environment Setup
- [ ] Verifikasi `uv` terinstall: `uv --version`
- [ ] `uv python pin 3.12`
- [ ] Buat `pyproject.toml` minimal → `uv sync`
- [ ] `uv sync --extra windows` berhasil
- [ ] Verifikasi: `uv run python -c "import sounddevice; print(sounddevice.query_devices())"`
- [ ] Verifikasi: `uv run python -c "import pyaudiowpatch; print('OK')"`
- [ ] Buat direktori `recordings/`, `scratch/`, `tests/unit/`, `tests/integration/`

### EP-01: Fondasi
- [ ] Buat semua direktori `src/meeting_recorder/` + sub-paket + `__init__.py`
- [ ] Isi `pyproject.toml` lengkap (semua dependency dari TDD §4)
- [ ] Implementasi `config/settings.py` + `pydantic-settings`
- [ ] Buat `.env.example`
- [ ] Tambahkan `[project.scripts]` entry point ke `pyproject.toml`
- [ ] Setup `[tool.ruff]` di `pyproject.toml`
- [ ] Setup `[tool.pytest.ini_options]` di `pyproject.toml`
- [ ] Verifikasi: `uv run ruff check src/` jalan
- [ ] Verifikasi: `uv run pytest` jalan (0 tests, tidak error)

### EP-02: Audio Capture
- [ ] Implementasi `capture/engine.py` — `AudioConfig` + `AudioCaptureEngine` ABC
- [ ] Implementasi `capture/engine.py` — `create_capture_engine()` factory
- [ ] Implementasi `capture/windows.py` — `list_devices()`
- [ ] Implementasi `capture/windows.py` — `_find_loopback_device()` dengan fallback
- [ ] Implementasi `capture/windows.py` — `_audio_callback()` + mixing logic
- [ ] Implementasi `capture/windows.py` — resample ke 16kHz jika native rate berbeda
- [ ] Implementasi `capture/windows.py` — downmix stereo ke mono
- [ ] Test manual: `uv run python scratch/test_capture.py` → WAV bisa diputar
- [ ] Implementasi `capture/macos.py` (bisa defer ke Sprint 2)
- [ ] Implementasi `capture/linux.py` (bisa defer ke Sprint 2)

### EP-03: Audio Processing
- [ ] Implementasi `processing/buffer.py` — `RingBuffer`
- [ ] Tambahkan warning log saat buffer overflow
- [ ] Implementasi `processing/chunker.py` — `AudioChunker`
- [ ] Test integrasi: buffer + chunker berjalan di thread terpisah
- [ ] Verifikasi offset calculation: chunk N mulai di `N * (chunk_duration - overlap)` detik

---

## Sprint 2 — Transcription + AI + CLI

### EP-04: Transcription
- [ ] Implementasi `transcription/engine.py` — `TranscriptSegment` + `TranscriptionEngine` ABC
- [ ] Implementasi `transcription/whisper_api.py` — `WhisperAPITranscriber`
- [ ] Tambahkan retry logic (exponential backoff, max 3x) untuk `RateLimitError`
- [ ] Tambahkan retry untuk `APITimeoutError`
- [ ] Test manual dengan WAV dari Sprint 1
- [ ] Implementasi `transcription/whisper_local.py` — `WhisperLocalTranscriber`
- [ ] Verifikasi tempfile cleanup di `finally` block

### EP-05: AI Pipeline
- [ ] Implementasi `ai/aggregator.py` — `TranscriptAggregator`
- [ ] Test deduplication: 4 segments input → 3 output (overlap di-skip)
- [ ] Implementasi `ai/summarizer.py` — `LLMSummarizer` ABC + `MeetingSummary`
- [ ] Implementasi `ai/gemini.py` — `GeminiSummarizer` dengan JSON parsing robust
- [ ] Implementasi `ai/openai_llm.py` — `OpenAISummarizer`
- [ ] Test manual summarize dengan transcript dummy

### EP-06: Output Management
- [ ] Implementasi `output/manager.py` — `OutputManager`
- [ ] Test: session dir dibuat dengan format `YYYYMMDD_HHMMSS`
- [ ] Test: 4 file tersimpan setelah `save_audio` + `save_transcript` + `save_summary`

### EP-07: CLI & Orchestration
- [ ] Implementasi `main.py` — skeleton CLI dengan Click
- [ ] Command `devices` — tampilkan device table dengan Rich
- [ ] Command `record` — wiring awal (tanpa display dulu)
- [ ] Implementasi `_record_async()` — setup semua komponen
- [ ] Hubungkan chunker callback ke asyncio via `call_soon_threadsafe`
- [ ] Implementasi stop via SIGINT + `asyncio.Event`
- [ ] Wait pending transcription tasks sebelum summarize
- [ ] Test end-to-end: `meeting-recorder record` → Ctrl+C → 4 file tersimpan
- [ ] Tambahkan Rich live display (elapsed, chunks, segments)
- [ ] Command `transcribe <file>` — transcribe WAV yang sudah ada
- [ ] Command `summarize <file>` — generate summary dari transcript .txt

---

## Sprint 3 — Detection + Testing + Polish

### EP-08: Meeting Auto-Detection
- [ ] Implementasi `detection/process_detector.py` — `ProcessDetector`
- [ ] Test: proses Zoom terdeteksi saat berjalan
- [ ] Implementasi `detection/network_detector.py` — `NetworkDetector`
- [ ] Test: port 8801 terdeteksi saat Zoom meeting aktif
- [ ] Implementasi `detection/window_detector.py` — `WindowDetector` Windows
- [ ] Implementasi `detection/window_detector.py` — `WindowDetector` macOS
- [ ] Implementasi `detection/window_detector.py` — `WindowDetector` Linux
- [ ] Implementasi `detection/audio_analyzer.py` — `AudioAnalyzer`
- [ ] Test: speech sample score > 7, musik score < 4
- [ ] Implementasi `detection/meeting_detector.py` — `MeetingDetector` state machine
- [ ] Verifikasi semua 9 skenario dari tabel Meeting Detection §5
- [ ] Integrasi `MeetingDetector` ke CLI command `watch`
- [ ] Command `status` — tampilkan breakdown skor saat ini

### EP-09: Testing
- [ ] `tests/unit/test_buffer.py` — push/pop, timeout, overflow
- [ ] `tests/unit/test_chunker.py` — overlap, WAV format, lifecycle
- [ ] `tests/unit/test_aggregator.py` — dedup, to_text, to_json, empty input
- [ ] `tests/unit/test_audio_analyzer.py` — speech vs music scoring
- [ ] `tests/unit/test_meeting_detector.py` — state transitions, callbacks
- [ ] `tests/integration/test_pipeline.py` — mock transcriber + mock summarizer
- [ ] Verifikasi: `uv run pytest tests/ -v` minimal 70% pass

### EP-10: Polish
- [ ] Error handling: loopback not found → fallback + instruksi
- [ ] Error handling: API timeout → retry + user notification
- [ ] Error handling: device disconnected → graceful stop + save partial
- [ ] Error handling: LLM JSON parse error → fallback response
- [ ] Tulis `README.md` — quick start, prerequisites, CLI usage, cost estimation
- [ ] Finalize `.env.example` dengan semua variable terdokumentasi
- [ ] Tambahkan `.gitignore` (recordings/, *.wav, .env, .venv/, *.log)
- [ ] Setup GitHub Actions CI (opsional untuk v0.1)

---

## Milestone Checklist

### ✅ Sprint 1 Done
- [ ] Audio pipeline capture → buffer → chunk berjalan
- [ ] WAV file dari WASAPI bisa diputar dan terdengar jelas
- [ ] Tidak ada race condition yang terdeteksi

### ✅ Sprint 2 Done
- [ ] `meeting-recorder record` berjalan end-to-end
- [ ] Setelah Ctrl+C, 4 file tersimpan di output dir
- [ ] Summary dalam Bahasa Indonesia yang coherent

### ✅ Sprint 3 Done (MVP v0.1)
- [ ] `meeting-recorder watch` start/stop otomatis saat meeting terdeteksi
- [ ] pytest suite berjalan tanpa error kritis
- [ ] README cukup untuk orang lain setup sendiri
- [ ] `.env.example` lengkap
