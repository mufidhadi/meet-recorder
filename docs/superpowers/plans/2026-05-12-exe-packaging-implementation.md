# Windows Executable Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone Windows executable (`.exe`) for Meet-Recorder using PyInstaller in `One-Directory` mode.

**Architecture:** 
- Add a utility to handle resource paths (relative to EXE vs Source).
- Configure PyInstaller to include all necessary dependencies (PyQt6, PyTorch, etc.) while excluding bloat.
- Keep data files (.env, recordings) external to the EXE folder for persistence.

**Tech Stack:** Python, PyInstaller, PyQt6.

---

### Task 1: Add Dependencies & Path Utility

**Files:**
- Modify: `pyproject.toml` (Add pyinstaller)
- Create: `meeting_recorder/utils/paths.py`

- [ ] **Step 1: Add PyInstaller to dev dependencies**
Run: `uv add --dev pyinstaller`

- [ ] **Step 2: Implement `get_base_path` utility**
```python
import os
import sys

def get_base_path():
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # But for --onedir, we often want the path relative to the EXE
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

def get_resource_path(relative_path):
    """Get path to internal bundled resource."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
```

- [ ] **Step 3: Update `Settings` to use `get_base_path`**
Modify `meeting_recorder/config/settings.py` to use `get_base_path()` for `.env` and `output_dir`.

- [ ] **Step 4: Commit**
`git add . && git commit -m "chore: add pyinstaller and path utility"`

---

### Task 2: Create PyInstaller Spec File

**Files:**
- Create: `meet_recorder.spec`

- [ ] **Step 1: Write the `.spec` file logic**
The spec file should:
- Point to `ui_app.py` as script.
- Include `meeting_recorder` package.
- Exclude `matplotlib`, `notebook`, `scipy` to save space.
- Set `console=False` for GUI mode.

```python
# meet_recorder.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['ui_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['google.generativeai', 'pydantic_settings', 'clr'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'scipy', 'tests', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Meet-Recorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Meet-Recorder',
)
```

- [ ] **Step 2: Commit**
`git add meet_recorder.spec && git commit -m "chore: add pyinstaller spec file"`

---

### Task 3: Build and Verify Executable

**Files:**
- Run: `uv run pyinstaller meet_recorder.spec`

- [ ] **Step 1: Run the build command**
Explain: "This will take a few minutes as it collects all dependencies including PyTorch."

- [ ] **Step 2: Verify folder structure**
Check `dist/Meet-Recorder/` exists and contains `Meet-Recorder.exe`.

- [ ] **Step 3: Test launch**
Launch `dist/Meet-Recorder/Meet-Recorder.exe` and verify GUI appears.

- [ ] **Step 4: Final Report**
Document size and usage instructions.
