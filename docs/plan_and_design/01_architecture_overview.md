# 01 — Arsitektur Sistem: Meeting Audio Recorder & AI Summarizer

> **Versi:** 1.0  
> **Tanggal:** April 2026  
> **Bahasa Implementasi:** Python (utama)

---

## 1. Latar Belakang & Motivasi

Integrasi SDK resmi platform meeting (Google Meet, Zoom, Microsoft Teams) memiliki hambatan teknis yang signifikan: OAuth flow yang kompleks, batasan kebijakan rekaman, approval proses yang panjang, dan perubahan API yang sering merusak integrasi yang sudah ada.

**Pendekatan alternatif:** Merekam audio langsung di **level perangkat (device-level audio capture)** — menangkap apapun yang keluar dari speaker dan masuk ke mikrofon, tanpa perlu menyentuh API platform manapun.

### Keunggulan Pendekatan Ini
| Aspek | SDK Platform | Device-Level Capture |
|---|---|---|
| Kompleksitas setup | Tinggi (OAuth, approval) | Rendah |
| Ketergantungan platform | Tinggi | Nol |
| Kompatibilitas | Per-platform | Universal |
| Maintenance | Tinggi (breaking changes) | Rendah |
| Legalitas perekaman | Bergantung ToS platform | Bergantung hukum setempat* |

> *Selalu informasikan peserta bahwa meeting direkam sesuai hukum yang berlaku.

---

## 2. Gambaran Sistem (High-Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SUMBER AUDIO                                  │
│                                                                       │
│   ┌─────────────────┐         ┌─────────────────┐                   │
│   │   System Audio  │         │   Microphone    │                   │
│   │  (Speaker Out)  │         │   (Mic In)      │                   │
│   │  Zoom/Meet/     │         │   Suara user    │                   │
│   │  Teams/Browser  │         │   lokal         │                   │
│   └────────┬────────┘         └────────┬────────┘                   │
└────────────┼──────────────────────────┼─────────────────────────────┘
             │                          │
             ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: AUDIO CAPTURE                            │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              AudioCaptureEngine                              │   │
│   │                                                               │   │
│   │  • WASAPI Loopback (Windows)                                 │   │
│   │  • ScreenCaptureKit / BlackHole (macOS)                      │   │
│   │  • PulseAudio Monitor (Linux)                                │   │
│   │                                                               │   │
│   │  Output: Raw PCM Audio Stream (16kHz, 16-bit, mono)         │   │
│   └─────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 2: AUDIO PROCESSING                         │
│                                                                       │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│   │ AudioBuffer  │───▶│AudioChunker  │───▶│  VAD (Voice Activity │  │
│   │              │    │              │    │  Detection)          │  │
│   │ Ring buffer  │    │ 30s chunks   │    │  (opsional)          │  │
│   │ thread-safe  │    │ overlap 2s   │    │                      │  │
│   └──────────────┘    └──────────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: TRANSCRIPTION                            │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              TranscriptionEngine                             │   │
│   │                                                               │   │
│   │  ┌─────────────────┐    ┌──────────────────────────────┐    │   │
│   │  │ Whisper API     │ OR │  Local Whisper (faster-       │    │   │
│   │  │ (OpenAI)        │    │  whisper / whisper.cpp)       │    │   │
│   │  └─────────────────┘    └──────────────────────────────┘    │   │
│   │                                                               │   │
│   │  Output: Timed transcript segments [{start, end, text}]     │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 4: AGGREGATION & AI                         │
│                                                                       │
│   ┌──────────────────────┐    ┌────────────────────────────────┐    │
│   │ TranscriptAggregator │───▶│      LLM Summarizer            │    │
│   │                      │    │                                 │    │
│   │ • Gabungkan segments │    │  • Gemini API (Google GenAI)   │    │
│   │ • Deduplikasi overlap│    │  • GPT-4o (OpenAI)             │    │
│   │ • Format timestamp   │    │  • Gemini (Google)             │    │
│   └──────────────────────┘    └────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 5: OUTPUT                                    │
│                                                                       │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│   │ Transcript    │  │   Summary     │  │  Audio Archive        │   │
│   │ (.txt / .json)│  │  (.md / .txt) │  │  (.wav / .mp3)        │   │
│   └───────────────┘  └───────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Komponen Utama

### 3.1 AudioCaptureEngine
Inti dari seluruh sistem. Bertanggung jawab menangkap audio dari level OS.

**Platform Support:**
- **Windows 10/11** → WASAPI Loopback via `sounddevice` / `pyaudiowpatch`
- **macOS 13+** → ScreenCaptureKit (Swift helper) atau BlackHole virtual audio device
- **Linux** → PulseAudio `monitor` source atau ALSA loopback

### 3.2 AudioChunker
Memotong audio stream yang terus berjalan menjadi potongan-potongan (chunks) yang bisa dikirim ke API transcription. Menggunakan strategi overlap untuk menghindari kata yang terpotong di batas chunk.

### 3.3 TranscriptionEngine
Mengirim audio chunk ke layanan speech-to-text dan mengembalikan segment transcript bertimestamp. Mendukung mode **streaming** (real-time) dan **batch** (post-meeting).

### 3.4 TranscriptAggregator
Mengumpulkan semua segment dari TranscriptionEngine, menggabungkannya secara kronologis, dan membersihkan duplikasi dari overlap.

### 3.5 LLMSummarizer
Mengambil full transcript dan menghasilkan summary terstruktur: ringkasan eksekutif, poin-poin keputusan, action items, dan peserta yang disebutkan.

### 3.6 OutputManager
Menyimpan semua artefak output: file audio, file transcript, dan file summary ke direktori yang terorganisasi.

---

## 4. Mode Operasi

### Mode A: Real-Time (Live Transcription)
```
Audio Stream → Chunk setiap 30 detik → Transcribe → Tampilkan di terminal
```
Cocok untuk: monitoring aktif, subtitle live.

### Mode B: Post-Meeting (Batch)
```
Rekam audio penuh → Simpan ke file → Transcribe seluruh file → Summarize
```
Cocok untuk: akurasi lebih tinggi, hemat API call.

### Mode C: Hybrid (Rekam + Live Summary Akhir)
```
Rekam audio penuh + transcribe real-time → Setelah meeting selesai → Generate summary
```
**Ini adalah mode yang direkomendasikan.**

---

## 5. Stack Teknologi

| Kategori | Pilihan Utama | Alternatif |
|---|---|---|
| Bahasa | Python 3.11+ | — |
| Audio Capture (Win) | `pyaudiowpatch` | `sounddevice` (WASAPI) |
| Audio Capture (Mac) | `BlackHole` + `sounddevice` | `ScreenCaptureKit` (Swift) |
| Audio Capture (Linux) | `sounddevice` (PulseAudio monitor) | `pyaudio` |
| Audio Processing | `numpy`, `scipy` | — |
| Transcription (cloud) | OpenAI Whisper API | Google Speech-to-Text |
| Transcription (lokal) | `faster-whisper` | `whisper.cpp` (via subprocess) |
| LLM Summarizer | Google Gemini API (`google-genai`) | OpenAI GPT-4o |
| Config Management | `pydantic-settings` | `dynaconf` |
| CLI Interface | `rich` + `click` | `typer` |
| Testing | `pytest` + `pytest-asyncio` | — |

---

## 6. Batasan & Pertimbangan

### Legalitas
- Di banyak yurisdiksi, merekam percakapan tanpa persetujuan semua pihak adalah ilegal.
- Selalu informasikan peserta meeting bahwa rekaman sedang berjalan.
- Ini adalah tanggung jawab pengguna, bukan aplikasi.

### Kualitas Audio
- System audio yang di-mix bisa menghasilkan kualitas lebih rendah dari rekaman langsung per-stream.
- Noise dari mikrofon bisa masuk dan mengurangi akurasi transcripsi.
- Solusi: terapkan noise reduction sebelum transcription.

### Privasi
- File audio dan transcript mengandung informasi sensitif.
- Pertimbangkan enkripsi at-rest untuk file output.
- Gunakan local Whisper jika konten meeting bersifat sangat rahasia.

---

## 7. Diagram Alur Data (Data Flow)

```
[Meeting berlangsung di PC]
        │
        ▼
[OS Audio Subsystem]
   ├── Output device (speaker) ──► [WASAPI/PulseAudio Loopback]
   └── Input device (mic)      ──► [Standard mic capture]
                                          │
                                          ▼
                               [AudioCaptureEngine.py]
                               • Mix system + mic audio
                               • Resample → 16kHz mono
                               • Push ke ring buffer
                                          │
                                          ▼ (setiap 30 detik)
                               [AudioChunker.py]
                               • Potong chunk
                               • 2 detik overlap
                               • Encode ke WAV/FLAC
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                    [Whisper API]          [faster-whisper lokal]
                              │                       │
                              └───────────┬───────────┘
                                          │
                                          ▼
                               [TranscriptAggregator.py]
                               • Merge segments
                               • Resolve overlap
                               • Format: [{ts, speaker?, text}]
                                          │
                                          ▼
                               [LLMSummarizer.py]
                               • Prompt ke Gemini/GPT
                               • Parse structured output
                                          │
                                          ▼
                               [OutputManager.py]
                               • /output/YYYYMMDD_HHMMSS/
                               •   ├── recording.wav
                               •   ├── transcript.json
                               •   ├── transcript.txt
                               •   └── summary.md
```
