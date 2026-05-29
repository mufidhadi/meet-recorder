# Output & CLI Orchestration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menyatukan semua komponen ke dalam satu interface CLI yang fungsional.

**Architecture:** `OutputManager` mengelola direktori sesi. CLI mengoordinasikan pipeline async menggunakan `asyncio`.

**Tech Stack:** Python 3.12, typer, rich.

---

### Task 8: Output Manager

**Files:**
- Create: `meeting_recorder/output/manager.py`
- Test: `tests/unit/test_output.py`

- [ ] **Step 1: Implement OutputManager**
(Logic untuk membuat folder `./recordings/YYYYMMDD_HHMMSS/` dan menyimpan file).

- [ ] **Step 2: Commit**
```bash
git add meeting_recorder/output/
git commit -m "feat: implement output manager for session storage"
```

---

### Task 9: CLI Orchestration (The Big One)

**Files:**
- Create: `meeting_recorder/cli/main.py`
- Modify: `pyproject.toml` (scripts entry point)

- [ ] **Step 1: Install CLI dependencies**
Run: `uv add typer rich`

- [ ] **Step 2: Implement Orchestration Logic**
(Fungsi `record` yang menyambungkan Capture -> Buffer -> Chunker -> Transcriber -> Aggregator -> Summarizer).

- [ ] **Step 3: Setup Entry Point**
Update `pyproject.toml` agar bisa dipanggil dengan command `meet-recorder`.

- [ ] **Step 4: Final Verification**
Run: `uv run meet-recorder --help`

- [ ] **Step 5: Commit**
```bash
git add meeting_recorder/cli/ pyproject.toml
git commit -m "feat: implement CLI orchestration and entry point"
```
