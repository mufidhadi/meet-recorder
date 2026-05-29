# 03 — Implementation Guide & Setup

> **Versi:** 1.0  
> **Tanggal:** April 2026

---

## 1. Prerequisites per Platform

### Windows
```
- Windows 10/11 (WASAPI Loopback support)
- Python 3.11+
- Visual C++ Build Tools (untuk kompilasi beberapa package)
```

### macOS
```
- macOS 12+ (Monterey atau lebih baru)
- Python 3.11+
- Homebrew
- BlackHole (virtual audio driver)
- Xcode Command Line Tools
```

### Linux
```
- Ubuntu 22.04+ / Debian 11+ / Arch
- Python 3.11+
- PulseAudio atau PipeWire (sudah ada di sebagian besar distro modern)
- ALSA utilities
```

---

## 2. Setup Step-by-Step

### 2.1 Clone & Install

```bash
# Clone project
git clone https://github.com/yourname/meeting-recorder.git
cd meeting-recorder

# Buat virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

# Install dependencies dasar
pip install -e .

# Install extras sesuai OS
pip install -e ".[windows]"     # Hanya Windows
```

### 2.2 Setup Platform-Specific

#### Windows — WASAPI Loopback

1. Install `pyaudiowpatch`:
   ```bash
   pip install pyaudiowpatch
   ```

2. Pastikan speaker default aktif. Tidak perlu konfigurasi tambahan — WASAPI Loopback device akan terdeteksi otomatis.

3. Verifikasi deteksi device:
   ```bash
   python -m meeting_recorder devices
   ```
   Output yang diharapkan:
   ```
   [0] Realtek Audio - Speakers (loopback=True)  ← System audio
   [1] Microphone (Realtek) (loopback=False)     ← Mic
   ```

#### macOS — BlackHole Setup

1. Install BlackHole:
   ```bash
   brew install blackhole-2ch
   ```

2. Buka **Audio MIDI Setup** (Spotlight → "Audio MIDI Setup"):
   - Klik `+` di pojok kiri bawah → "Create Multi-Output Device"
   - Centang: **BlackHole 2ch** + speaker asli kamu (Built-in Output / AirPods / dll)
   - Rename jadi "Meeting Recorder"

3. Set "Meeting Recorder" sebagai **default output** di System Settings → Sound → Output.

4. Verifikasi:
   ```bash
   python -m meeting_recorder devices
   # Pastikan "BlackHole 2ch" muncul sebagai input device
   ```

   > **Tips:** Suara dari speaker tetap akan keluar normal karena Multi-Output Device meneruskan ke speaker asli sekaligus ke BlackHole.

#### Linux — PulseAudio Monitor

Tidak perlu instalasi tambahan. PulseAudio `monitor` source sudah otomatis tersedia.

```bash
# Cek monitor source yang tersedia
pactl list sources short | grep monitor

# Output contoh:
# 1  alsa_output.pci-0000_00_1f.3.analog-stereo.monitor  ...
```

Jika menggunakan PipeWire (Ubuntu 22.04+):
```bash
# PipeWire kompatibel dengan PulseAudio API, tidak perlu perubahan
# Verifikasi:
pactl info | grep "Server Name"
# Server Name: PulseAudio (on PipeWire ...)  ← OK
```

---

### 2.3 Konfigurasi Environment

Buat file `.env` dari template:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Pilih salah satu atau keduanya
OPENAI_API_KEY=sk-...         # Untuk Whisper API + GPT (opsional)
GEMINI_API_KEY=AIza...        # Untuk Gemini summarizer

# Konfigurasi audio (opsional, ada default)
TRANSCRIPTION_BACKEND=whisper_api    # atau: whisper_local
LANGUAGE=id                          # id=Indonesia, en=English, auto=auto-detect
LLM_BACKEND=gemini                   # atau: openai
```

---

## 3. Cara Pakai (CLI Usage)

### Perintah Dasar

```bash
# Lihat daftar audio device
python -m meeting_recorder devices

# Rekam meeting (mode hybrid: rekam + transcribe + summarize setelah selesai)
python -m meeting_recorder record

# Rekam dengan opsi custom
python -m meeting_recorder record \
  --duration 90 \           # Durasi maksimal dalam menit (0 = sampai Ctrl+C)
  --output ./my-recordings \
  --language en \
  --no-mic \                # Skip microphone (hanya system audio)
  --backend whisper_local   # Pakai local Whisper

# Transcribe file audio yang sudah ada (tanpa merekam ulang)
python -m meeting_recorder transcribe recording.wav

# Hanya buat summary dari file transcript yang sudah ada
python -m meeting_recorder summarize transcript.txt
```

### Flow Interaktif

Saat `record` dijalankan, tampilan di terminal:
```
╭─── Meeting Recorder ──────────────────────────────────────────────╮
│  🎙  Capturing: System Audio + Microphone                          │
│  📝  Transcription: Whisper API (id)                               │
│  🤖  Summarizer: Gemini (gemini-2.5-flash)                      │
│  💾  Output: ./recordings/20260424_143022/                         │
╰───────────────────────────────────────────────────────────────────╯

⏱  00:05:32  |  Chunks processed: 11  |  Segments: 89

[00:00:04] Oke, jadi agenda hari ini ada tiga poin utama...
[00:00:18] Yang pertama soal timeline project Q3...
[00:00:31] Betul, kita perlu finalize vendor list paling lambat Jumat...

[Ctrl+C untuk stop dan generate summary]
```

Setelah Ctrl+C:
```
⏹  Recording stopped. Generating summary...

✅ Summary generated!

📁 Files saved:
   ./recordings/20260424_143022/
   ├── recording.wav        (45.2 MB)
   ├── transcript.json      (128 KB)
   ├── transcript.txt       (48 KB)
   └── summary.md           (3.1 KB)

─── Summary Preview ─────────────────────────────────────────────────
# Meeting Summary

## Executive Summary
Meeting membahas timeline project Q3, pemilihan vendor untuk infrastruktur
baru, dan review budget Q2 yang telah selesai.

## Key Decisions
- Vendor final akan dipilih maksimal Jumat 26 April
- Timeline project Q3 digeser 2 minggu dari rencana awal
...
```

---

## 4. Implementasi `main.py` (Entry Point)

```python
# src/meeting_recorder/main.py
import asyncio
import signal
import sys
import click
from rich.console import Console
from rich.live import Live
from rich.table import Table
from datetime import datetime

from .config.settings import Settings
from .capture.engine import AudioConfig, create_capture_engine
from .processing.buffer import RingBuffer
from .processing.chunker import AudioChunker
from .transcription.whisper_api import WhisperAPITranscriber
from .transcription.whisper_local import WhisperLocalTranscriber
from .ai.aggregator import TranscriptAggregator
from .ai.gemini import GeminiSummarizer
from .ai.openai_llm import OpenAISummarizer
from .output.manager import OutputManager

console = Console()

@click.group()
def cli():
    """Meeting Recorder — Rekam, transcribe, dan summarize meeting otomatis."""
    pass

@cli.command()
def devices():
    """List semua audio device yang tersedia."""
    settings = Settings()
    config = AudioConfig()
    
    # Gunakan dummy callback untuk list devices
    engine = create_capture_engine(config, lambda x: None)
    device_list = engine.list_devices()
    
    table = Table(title="Available Audio Devices")
    table.add_column("Index", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="green")
    
    for d in device_list:
        device_type = "🔊 Loopback" if d.get("is_loopback") else "🎙 Input"
        table.add_row(str(d["index"]), d["name"], device_type)
    
    console.print(table)

@cli.command()
@click.option("--duration", default=0, help="Durasi max dalam menit (0=unlimited)")
@click.option("--output", default="./recordings", help="Direktori output")
@click.option("--language", default=None, help="Kode bahasa (id, en, auto)")
@click.option("--no-mic", is_flag=True, help="Skip microphone capture")
@click.option("--backend", default=None, help="whisper_api atau whisper_local")
def record(duration, output, language, no_mic, backend):
    """Mulai merekam meeting."""
    asyncio.run(_record_async(duration, output, language, no_mic, backend))

async def _record_async(duration, output, language, no_mic, backend):
    settings = Settings()
    
    # Override settings dari CLI args
    if language:
        settings.language = language
    if backend:
        settings.transcription_backend = backend
    if no_mic:
        settings.capture_microphone = False

    # Inisialisasi komponen
    output_mgr = OutputManager(output)
    session_id = output_mgr.start_session()
    
    ring_buffer = RingBuffer(maxsize_seconds=60, sample_rate=settings.sample_rate)
    aggregator = TranscriptAggregator()
    
    # Pilih transcriber
    if settings.transcription_backend == "whisper_local":
        transcriber = WhisperLocalTranscriber(
            model_size=settings.whisper_model_size,
            language=settings.language,
        )
    else:
        transcriber = WhisperAPITranscriber(
            api_key=settings.openai_api_key,
            language=settings.language,
        )

    # Chunk counter untuk offset waktu
    chunk_offset = 0.0

    async def handle_chunk(wav_bytes: bytes, chunk_index: int):
        nonlocal chunk_offset
        offset = chunk_index * (settings.chunk_duration_s - settings.overlap_s)
        segments = await transcriber.transcribe(wav_bytes, chunk_index, offset)
        aggregator.add_segments(segments)
        # Print latest segments ke terminal
        for seg in segments[-3:]:
            ts = TranscriptAggregator._format_time(seg.start_time)
            console.print(f"[dim][{ts}][/dim] {seg.text}")

    def audio_callback(data):
        ring_buffer.push(data)

    # Setup capture
    audio_config = AudioConfig(
        sample_rate=settings.sample_rate,
        capture_system_audio=settings.capture_system_audio,
        capture_microphone=settings.capture_microphone,
    )
    capture_engine = create_capture_engine(audio_config, audio_callback)

    # Chunker dengan async callback
    def sync_chunk_callback(wav_bytes, chunk_idx):
        asyncio.create_task(handle_chunk(wav_bytes, chunk_idx))

    chunker = AudioChunker(
        ring_buffer=ring_buffer,
        sample_rate=settings.sample_rate,
        chunk_duration_s=settings.chunk_duration_s,
        overlap_s=settings.overlap_s,
        on_chunk=sync_chunk_callback,
    )

    # Start recording
    console.print(f"\n[bold green]🎙 Recording started[/bold green] (Ctrl+C to stop)\n")
    capture_engine.start()
    chunker.start()

    # Handle stop signal
    stop_event = asyncio.Event()
    
    def on_signal(*_):
        stop_event.set()
    
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, on_signal)
    
    # Wait untuk stop atau duration habis
    if duration > 0:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=duration * 60)
        except asyncio.TimeoutError:
            pass
    else:
        await stop_event.wait()

    # Stop capture
    capture_engine.stop()
    chunker.stop()
    
    console.print("\n[bold yellow]⏹ Recording stopped. Generating summary...[/bold yellow]")

    # Generate summary
    if settings.llm_backend == "gemini":
        summarizer = GeminiSummarizer(settings.gemini_api_key, settings.gemini_model)
    else:
        summarizer = OpenAISummarizer(settings.openai_api_key, settings.openai_model)

    transcript_text = aggregator.to_text()
    summary = await summarizer.summarize(transcript_text)

    # Save outputs
    output_mgr.save_transcript(aggregator.to_json())
    output_mgr.save_summary(summary.raw_markdown)

    console.print(f"\n[bold green]✅ Done![/bold green]")
    console.print(f"📁 Output: {output_mgr.session_dir}/")

if __name__ == "__main__":
    cli()
```

---

## 5. Testing Strategy

### Unit Tests

```python
# tests/unit/test_chunker.py
import numpy as np
import pytest
from meeting_recorder.processing.buffer import RingBuffer
from meeting_recorder.processing.chunker import AudioChunker

def test_ring_buffer_push_pop():
    buf = RingBuffer(maxsize_seconds=10, sample_rate=16000)
    data = np.ones(1600, dtype=np.int16)
    buf.push(data)
    assert len(buf) == 1600
    popped = buf.pop(1600)
    assert popped is not None
    assert len(popped) == 1600

def test_chunker_overlap():
    """Pastikan overlap data carried forward dengan benar."""
    buf = RingBuffer(maxsize_seconds=60, sample_rate=16000)
    chunks_received = []
    
    chunker = AudioChunker(
        ring_buffer=buf,
        sample_rate=16000,
        chunk_duration_s=5.0,
        overlap_s=1.0,
        on_chunk=lambda wav, idx: chunks_received.append(idx),
    )
    
    # Push 10 detik data
    buf.push(np.zeros(160_000, dtype=np.int16))
    chunker.start()
    import time; time.sleep(2)
    chunker.stop()
    
    assert len(chunks_received) >= 1
```

```python
# tests/unit/test_aggregator.py
from meeting_recorder.ai.aggregator import TranscriptAggregator
from meeting_recorder.transcription.engine import TranscriptSegment

def test_deduplicate_overlap():
    agg = TranscriptAggregator(overlap_tolerance_s=1.5)
    
    # Simulasi dua chunk dengan overlap
    agg.add_segments([
        TranscriptSegment(0, 0.0, 5.0, "Halo semua"),
        TranscriptSegment(0, 5.0, 10.0, "Kita mulai meeting"),
        TranscriptSegment(1, 9.0, 14.0, "Agenda hari ini"),  # overlap!
        TranscriptSegment(1, 14.0, 18.0, "Ada tiga poin"),
    ])
    
    deduped = agg.deduplicate()
    # Segment di 9.0 harus di-skip karena overlap dengan 10.0
    assert len(deduped) == 3
    texts = [s.text for s in deduped]
    assert "Agenda hari ini" not in texts
```

### Integration Test

```python
# tests/integration/test_pipeline.py
import asyncio
import numpy as np
import pytest

@pytest.mark.asyncio
async def test_full_pipeline_mock():
    """Test pipeline end-to-end dengan mock transcriber."""
    from unittest.mock import AsyncMock, patch
    from meeting_recorder.transcription.engine import TranscriptSegment
    
    mock_segments = [
        TranscriptSegment(0, 0.0, 5.0, "Test transcript"),
    ]
    
    with patch(
        "meeting_recorder.transcription.whisper_api.WhisperAPITranscriber.transcribe",
        new_callable=AsyncMock,
        return_value=mock_segments,
    ):
        # ... jalankan pipeline dengan audio sintetis
        pass
```

---

## 6. Optimisasi & Tips

### Akurasi Transcription
- Gunakan **prompt** di Whisper API untuk memasukkan nama peserta dan istilah teknis:
  ```python
  transcriber = WhisperAPITranscriber(
      api_key=key,
      prompt="Meeting tentang product roadmap. Peserta: Budi, Sari, Ahmad. Istilah: sprint, backlog, MVP, CI/CD."
  )
  ```
- Gunakan model `large-v3` untuk akurasi tertinggi (local) meskipun lebih lambat.
- Pertimbangkan VAD (Voice Activity Detection) untuk skip silence dan hemat API cost.

### Performa
| Konfigurasi | Latency | Cost | Akurasi |
|---|---|---|---|
| Whisper API + GPT-4o | Rendah | Tinggi | Tinggi |
| Whisper API + Gemini | Rendah | Menengah | Sangat Tinggi |
| faster-whisper (medium) + Gemini | Menengah | Rendah* | Tinggi |
| faster-whisper (large-v3) + Gemini | Tinggi | Rendah* | Sangat Tinggi |

*Hanya bayar Gemini API, Whisper lokal gratis.

### Estimasi Biaya (Whisper API)
- Whisper API: $0.006 / menit audio
- Meeting 1 jam = 60 × $0.006 = **$0.36** untuk transcription
- Gemini summary: ~$0.005-0.02 tergantung panjang transcript (jauh lebih murah)
- Total 1 jam meeting: **~$0.40-0.50**

### Hemat Biaya
- Gunakan `faster-whisper` model `medium` untuk meeting internal
- Simpan transcript lokal, regenerate summary jika perlu tanpa re-transcribe
- Terapkan VAD untuk skip silence (bisa hemat 20-40% audio duration)

---

## 7. Known Issues & Workarounds

### macOS: Tidak ada audio di BlackHole setelah restart
**Gejala:** BlackHole tidak menangkap audio setelah restart macOS.  
**Fix:** Re-set Multi-Output Device sebagai default output di System Settings.  
**Prevention:** Buat script startup atau gunakan `SwitchAudioSource` via Homebrew.

```bash
brew install switchaudio-osx
# Set di login script:
SwitchAudioSource -s "Meeting Recorder"
```

### Windows: Audio terputus saat device switch (headset disconnect)
**Gejala:** Exception saat headset/speaker dicabut mid-recording.  
**Fix:** Tangkap exception di audio callback dan restart stream dengan device baru.

### Linux PipeWire: Monitor source tidak ditemukan
**Gejala:** `pactl list sources` tidak menampilkan `.monitor` source.  
**Fix:**
```bash
# Install PulseAudio compatibility layer
sudo apt install pipewire-pulse
systemctl --user restart pipewire pipewire-pulse
```

### Whisper: Bahasa Indonesia sering dideteksi sebagai Melayu
**Fix:** Set `language="id"` secara eksplisit, jangan pakai `language="auto"` untuk konten Indonesia.

---

## 8. Roadmap Pengembangan

### v0.1 — MVP
- [x] Desain arsitektur
- [ ] Windows WASAPI Loopback
- [ ] Whisper API transcription  
- [ ] Gemini summarization
- [ ] CLI sederhana

### v0.2 — Multi-platform
- [ ] macOS BlackHole support
- [ ] Linux PulseAudio support
- [ ] Local Whisper (faster-whisper)

### v0.3 — UX Polish
- [ ] Real-time transcript display (rich Live)
- [ ] Speaker diarization (siapa berbicara)
- [ ] GUI sederhana (Tkinter / web UI)

### v0.4 — Advanced Features
- [ ] Export ke Notion / Confluence
- [ ] Integrasi kalender (ambil judul meeting otomatis)
- [ ] Multi-language meeting support
- [ ] Enkripsi file output at-rest

---

## 9. Referensi

| Resource | URL |
|---|---|
| PyAudioWPatch (WASAPI Loopback) | https://github.com/s0d3s/PyAudioWPatch |
| sounddevice docs | https://python-sounddevice.readthedocs.io |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper |
| BlackHole (macOS) | https://github.com/ExistentialAudio/BlackHole |
| OpenAI Whisper API | https://platform.openai.com/docs/api-reference/audio |
| Google Gemini API | https://ai.google.dev/gemini-api/docs |
| PulseAudio Monitor Sources | https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/ |
