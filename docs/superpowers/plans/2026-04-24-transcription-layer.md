# Transcription Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi pengiriman audio chunk ke OpenAI Whisper API dan penggabungan hasilnya.

**Architecture:** `WhisperAPITranscriber` mengimplementasikan interface `Transcriber`. `TranscriptAggregator` mengelola urutan teks dan timestamp.

**Tech Stack:** Python 3.12, openai, pydantic.

---

### Task 5: Transcription Engine & Whisper API

**Files:**
- Create: `meeting_recorder/transcription/engine.py` (ABC)
- Create: `meeting_recorder/transcription/whisper_api.py`
- Create: `meeting_recorder/data/transcription.py` (Dataclasses)

- [ ] **Step 1: Define Transcription Data Models**
File: `meeting_recorder/data/transcription.py`
```python
from pydantic import BaseModel
from typing import List

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str

class TranscriptResult(BaseModel):
    segments: List[TranscriptSegment]
    full_text: str
```

- [ ] **Step 2: Create Transcriber ABC**
File: `meeting_recorder/transcription/engine.py`
```python
from abc import ABC, abstractmethod
from meeting_recorder.data.transcription import TranscriptResult

class Transcriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        pass
```

- [ ] **Step 3: Implement WhisperAPITranscriber**
File: `meeting_recorder/transcription/whisper_api.py`
(Akan menggunakan library `openai` secara async).

- [ ] **Step 4: Commit**
```bash
git add meeting_recorder/transcription/ meeting_recorder/data/transcription.py
git commit -m "feat: add transcription engine interfaces and models"
```

---

### Task 6: Transcript Aggregator

**Files:**
- Create: `meeting_recorder/ai/aggregator.py`
- Test: `tests/unit/test_aggregator.py`

- [ ] **Step 1: Implement Aggregator**
(Logic untuk menyambungkan text dari berbagai chunk berdasarkan offset waktu).

- [ ] **Step 2: Commit**
```bash
git add meeting_recorder/ai/aggregator.py
git commit -m "feat: implement transcript aggregator"
```
