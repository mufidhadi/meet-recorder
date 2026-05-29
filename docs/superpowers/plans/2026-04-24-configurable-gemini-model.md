# Gemini Model Configuration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memindahkan hardcoded model name Gemini ke dalam configuration (Settings & .env).

**Architecture:** Update `Settings` Pydantic model dan sesuaikan `GeminiTranscriber` serta `GeminiSummarizer`.

---

### Task 14: Configurable Gemini Model

**Files:**
- Modify: `meeting_recorder/config/settings.py`
- Modify: `meeting_recorder/transcription/gemini_transcriber.py`
- Modify: `meeting_recorder/ai/gemini.py`
- Modify: `meeting_recorder/cli/main.py`

- [ ] **Step 1: Update Settings to include Gemini Model ID**
File: `meeting_recorder/config/settings.py`
```python
class Settings(BaseSettings):
    # ... existing fields ...
    gemini_model_id: str = "gemini-2.0-flash" 
```

- [ ] **Step 2: Update GeminiTranscriber to use model from settings**
File: `meeting_recorder/transcription/gemini_transcriber.py`
```python
class GeminiTranscriber(Transcriber):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
```

- [ ] **Step 3: Update CLI to pass the model name from settings**
File: `meeting_recorder/cli/main.py`
Pass `settings.gemini_model_id` to both Transcriber and Summarizer.

- [ ] **Step 4: Commit**
```bash
git add meeting_recorder/
git commit -m "feat: make Gemini model ID configurable via settings and .env"
```
