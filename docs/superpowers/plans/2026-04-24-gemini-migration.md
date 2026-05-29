# Gemini-only Transcription Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mengganti OpenAI Whisper dengan Google Gemini 1.5 Flash untuk transkripsi audio.

**Architecture:** Implementasi `GeminiTranscriber` yang mengirim audio bytes langsung ke Gemini API.

**Tech Stack:** Python 3.12, google-generativeai.

---

### Task 10: Gemini Transcriber

**Files:**
- Create: `meeting_recorder/transcription/gemini_transcriber.py`
- Modify: `meeting_recorder/cli/main.py`
- Modify: `meeting_recorder/config/settings.py`

- [ ] **Step 1: Implement GeminiTranscriber**
File: `meeting_recorder/transcription/gemini_transcriber.py`
```python
import google.generativeai as genai
from meeting_recorder.transcription.engine import Transcriber
from meeting_recorder.data.transcription import TranscriptResult, TranscriptSegment

class GeminiTranscriber(Transcriber):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        # Gemini 1.5 Flash supports audio bytes directly via parts
        response = self.model.generate_content([
            "Tolong buatkan transkrip dari audio ini secara verbatim (kata per kata).",
            {"mime_type": "audio/wav", "data": audio_bytes}
        ])
        
        # Note: Gemini usually returns full text. 
        # For timestamps, we would need a more specific prompt or different API call.
        # For MVP, we'll treat the whole chunk as one segment.
        text = response.text.strip()
        return TranscriptResult(
            segments=[TranscriptSegment(start=0.0, end=30.0, text=text)],
            full_text=text
        )
```

- [ ] **Step 2: Update CLI to use GeminiTranscriber**
File: `meeting_recorder/cli/main.py`
(Ganti `WhisperAPITranscriber` dengan `GeminiTranscriber` dan hapus pengecekan `openai_api_key`).

- [ ] **Step 3: Clean up Settings**
File: `meeting_recorder/config/settings.py`
(Hapus `openai_api_key`).

- [ ] **Step 4: Commit**
```bash
git add meeting_recorder/
git commit -m "feat: migrate transcription to Google Gemini (OpenAI-free)"
```
