# Meeting Detection (Auto-Mode) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menambahkan fitur pendeteksian otomatis aplikasi meeting (Zoom, Meet, Teams) untuk memulai rekaman tanpa campur tangan manual.

**Architecture:** 
- `MeetingDetector` berjalan di loop background untuk memantau proses Windows.
- Perintah CLI baru `auto` yang menunggu meeting dimulai, merekam, lalu kembali menunggu (looping).
- Shortcut `record_auto.cmd`.

**Tech Stack:** Python 3.12, psutil.

---

### Task 18: Meeting Detection Logic

**Files:**
- Modify: `pyproject.toml`
- Create: `meeting_recorder/capture/detector.py`
- Modify: `meeting_recorder/cli/main.py`
- Create: `record_auto.cmd`

- [ ] **Step 1: Install dependencies**
Run: `uv add psutil`

- [ ] **Step 2: Implement MeetingDetector**
File: `meeting_recorder/capture/detector.py`
(Logic untuk mendeteksi proses `Zoom.exe`, `Teams.exe`, atau tab browser yang mengandung kata "Meet").

- [ ] **Step 3: Add 'auto' command to CLI**
File: `meeting_recorder/cli/main.py`
```python
@app.command()
def auto():
    """Wait for a meeting to start and record automatically."""
    # Logic: 
    # 1. Start detector loop.
    # 2. When meeting found: call _record_async.
    # 3. When meeting closed: _record_async naturally stops (via silence or manual).
    # 4. Repeat.
```

- [ ] **Step 4: Create record_auto.cmd**
File: `record_auto.cmd`
```batch
@echo off
pushd "%~dp0"
echo Meet-Recorder (AUTO MODE) is waiting for a meeting...
uv run python main.py auto
popd
pause
```

- [ ] **Step 5: Commit & Tag**
```bash
git add .
git commit -m "feat: implement meeting detection and auto-record mode"
git tag -a v0.2.0-auto -m "Release v0.2: Automatic Meeting Detection"
```
