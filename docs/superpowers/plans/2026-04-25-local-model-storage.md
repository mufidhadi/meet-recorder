# Local Model Storage Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memindahkan lokasi penyimpanan model HuggingFace ke dalam folder proyek `./models/`.

**Architecture:** Update `LocalHFTranscriber` agar menggunakan parameter `model_kwargs` dengan `cache_dir` saat inisialisasi pipeline.

---

### Task 17: Project-Local Model Storage

**Files:**
- Modify: `meeting_recorder/transcription/local_hf.py`

- [ ] **Step 1: Update LocalHFTranscriber to use project directory**
File: `meeting_recorder/transcription/local_hf.py`
```python
class LocalHFTranscriber(Transcriber):
    def __init__(self, model_id: str):
        import torch
        import os
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Ensure models directory exists
        os.makedirs("./models", exist_ok=True)
        
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model_id,
            device=device,
            model_kwargs={"cache_dir": "./models"} 
        )
```

- [ ] **Step 2: Commit**
```bash
git add meeting_recorder/transcription/local_hf.py
git commit -m "feat: store local models inside project directory for portability"
```
