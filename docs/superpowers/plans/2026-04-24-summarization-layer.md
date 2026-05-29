# Summarization Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi perangkuman transkrip menggunakan Google Gemini API.

**Architecture:** `GeminiSummarizer` mengimplementasikan interface `Summarizer`. Menghasilkan output dalam format Markdown terstruktur.

**Tech Stack:** Python 3.12, google-generativeai.

---

### Task 7: Summarization Engine & Gemini API

**Files:**
- Create: `meeting_recorder/ai/summarizer.py` (ABC)
- Create: `meeting_recorder/ai/gemini.py`
- Create: `meeting_recorder/data/summary.py` (Dataclasses)

- [ ] **Step 1: Define Summary Data Models**
File: `meeting_recorder/data/summary.py`
```python
from pydantic import BaseModel

class MeetingSummary(BaseModel):
    title: str
    raw_markdown: str
```

- [ ] **Step 2: Create Summarizer ABC**
File: `meeting_recorder/ai/summarizer.py`
```python
from abc import ABC, abstractmethod
from meeting_recorder.data.summary import MeetingSummary

class Summarizer(ABC):
    @abstractmethod
    async def summarize(self, transcript_text: str) -> MeetingSummary:
        pass
```

- [ ] **Step 3: Update dependencies**
Run: `uv add google-generativeai`

- [ ] **Step 4: Implement GeminiSummarizer**
File: `meeting_recorder/ai/gemini.py`
(Menggunakan model `gemini-1.5-flash` untuk kecepatan dan biaya rendah).

- [ ] **Step 5: Commit**
```bash
git add meeting_recorder/ai/ meeting_recorder/data/summary.py
git commit -m "feat: implement summarization engine with Google Gemini"
```
