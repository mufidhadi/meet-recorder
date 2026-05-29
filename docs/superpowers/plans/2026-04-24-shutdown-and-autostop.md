# Graceful Shutdown & Auto-Stop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memastikan summarizer selalu berjalan saat aplikasi berhenti, dan menambahkan fitur Auto-Stop jika terdeteksi keheningan yang lama.

**Architecture:** 
- Gunakan `asyncio.Event` untuk kontrol stop yang lebih bersih.
- Tambahkan `silent_chunks_count` di orchestrator untuk memicu stop otomatis.
- Pindahkan logic finalization (save & summarize) ke fungsi terpisah yang dijamin terpanggil.

---

### Task 15: Graceful Shutdown & Auto-Stop Logic

**Files:**
- Modify: `meeting_recorder/cli/main.py`

- [ ] **Step 1: Improve Orchestration Logic**
Modify `_record_async` to use an explicit `stop_event` and monitor silence.
```python
async def _record_async(settings: Settings, chunk_size: float, output_dir: str):
    # ... setup components ...
    
    stop_event = asyncio.Event()
    silent_chunks_consecutive = 0
    max_silent_chunks = 6 # 1 minute if chunk_size is 10s
    
    def on_chunk_ready(wav_bytes):
        nonlocal chunk_index, silent_chunks_consecutive
        # Note: In Task 12 we added silence detection in chunker. 
        # We need to communicate back to CLI if a chunk was silent.
        # Let's modify on_chunk_ready to accept a 'is_silent' flag.
        pass

# Actually, let's simplify: the CLI handles the stop event.
```

- [ ] **Step 2: Refactor Chunker to report silence**
File: `meeting_recorder/processing/chunker.py`
Modify `on_chunk_callback` to pass info about the chunk.

- [ ] **Step 3: Update CLI to handle Signal and Auto-Stop**
File: `meeting_recorder/cli/main.py`
```python
    try:
        engine.start()
        chunker.start()
        while not stop_event.is_set():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Guarantee summarization runs here
```

- [ ] **Step 4: Commit**
```bash
git add meeting_recorder/
git commit -m "feat: implement graceful shutdown, auto-stop on silence, and terminal logging"
```
