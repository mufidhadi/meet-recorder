# Design Doc: Core Audio Pipeline & Transcription MVP
**Date:** 2026-04-24
**Topic:** Sprint 1 & 2 Core Implementation

## 1. Overview
Membangun pipeline audio yang ringan (low-resource) untuk Windows menggunakan WASAPI loopback, diintegrasikan dengan OpenAI Whisper API untuk transcription dan Gemini/OpenAI untuk summarization.

## 2. Architecture Components

### A. Capture Layer (`meeting_recorder.capture`)
- **`AudioConfig`**: Single source of truth untuk audio parameters (16kHz, Mono, Int16).
- **`WindowsCaptureEngine`**: Menggunakan `pyaudiowpatch` untuk menangkap system audio (loopback) dan microphone.
- **Mixing Logic**: Penjumlahan linear sederhana dengan clipping protection untuk menggabungkan Mic + System audio dalam callback thread.

### B. Processing Layer (`meeting_recorder.processing`)
- **`RingBuffer`**: Berbasis NumPy array dengan fixed-size. Menyimpan raw PCM data.
- **`AudioChunker`**: Mengambil data dari `RingBuffer` setiap $N$ detik (default 30s) dan mengkonversinya menjadi format WAV bytes di memory (io.BytesIO).

### C. Transcription & AI Layer
- **`WhisperAPITranscriber`**: Mengirim WAV bytes ke OpenAI `v1/audio/transcriptions`.
- **`TranscriptAggregator`**: Menggabungkan segmen-segmen transkrip dengan timestamp yang akurat.
- **`GeminiSummarizer`**: Menggunakan `google-generativeai` untuk merangkum hasil akhir.

## 3. Data Flow
`WASAPI Loopback + Mic` -> `Callback (Mixing)` -> `RingBuffer` -> `Chunker (30s)` -> `Whisper API` -> `Aggregator` -> `LLM Summary` -> `Output Manager (Disk)`

## 4. Testing Strategy (TDD)
1. **Unit Tests**:
   - `RingBuffer`: Push/pop logic, overflow handling.
   - `AudioChunker`: Validasi WAV header dan durasi chunk.
   - `Aggregator`: Penggabungan teks dengan overlap handling.
2. **Integration Tests**:
   - Mocking Whisper API response.
   - Pipeline flow dari Buffer ke Chunker.
3. **Manual Validation**:
   - `scratch/check_audio.py` untuk mendengarkan hasil rekaman awal.

## 5. Error Handling
- **Audio Device Disconnect**: Graceful stop dan log error.
- **API Timeout**: Retry logic dengan exponential backoff untuk Whisper/Gemini calls.
- **Buffer Overflow**: Log warning dan drop data tertua (Circular buffer behavior).

## 6. Project Structure
```text
meeting_recorder/
├── config/settings.py
├── capture/
│   ├── engine.py
│   └── windows.py
├── processing/
│   ├── buffer.py
│   └── chunker.py
├── transcription/
│   ├── engine.py
│   └── whisper_api.py
├── ai/
│   ├── summarizer.py
│   └── gemini.py
├── output/manager.py
└── cli/main.py
```
