# Entry Point & Shortcut Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menyederhanakan eksekusi program agar tidak perlu mengetik command panjang.

**Architecture:** 
- `main.py` akan memanggil Typer app secara langsung.
- `record.cmd` akan membungkus perintah `uv run`.

---

### Task 16: Simplified Entry Point

**Files:**
- Modify: `main.py`
- Create: `record.cmd`

- [ ] **Step 1: Link main.py to CLI**
File: `main.py`
```python
from meeting_recorder.cli.main import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Create Windows Shortcut Script**
File: `record.cmd`
```batch
@echo off
uv run python main.py record --chunk-size 15
```

- [ ] **Step 3: Commit**
```bash
git add main.py record.cmd
git commit -m "chore: add main.py entry point and record.cmd shortcut"
```
