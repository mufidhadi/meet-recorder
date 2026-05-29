# Meet-Recorder Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a native Windows desktop application using PyQt6 to manage, record, and replay meetings with AI-powered features.

**Architecture:** Model-View-Controller (MVC) with QThreads for background processing.
- **Model**: `RecordingSession` and `SessionManager` to interface with the filesystem.
- **View**: Modular PyQt6 widgets (`Sidebar`, `RecordingTab`, `HistoryTab`, `PlayerBar`).
- **Controller**: `MainController` to orchestrate data flow between UI and backend engines.

**Tech Stack:** Python 3.12, PyQt6, QtMultimedia, NumPy (for VU meters), existing Meet-Recorder AI/Capture modules.

---

### Task 1: Project Setup & Base UI Boilerplate

**Files:**
- Create: `meeting_recorder/ui/__init__.py`
- Create: `meeting_recorder/ui/main_window.py`
- Create: `ui_app.py` (Entry point)
- Modify: `pyproject.toml` (Add PyQt6)

- [ ] **Step 1: Add PyQt6 dependency**
Run: `uv add PyQt6`

- [ ] **Step 2: Create Main Window Boilerplate**
```python
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QTabWidget, QApplication
import sys

class MeetRecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meet-Recorder")
        self.setMinimumSize(1000, 700)
        
        # Central Widget & Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QHBoxLayout(central)
        
        # Sidebar placeholder
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet("background-color: #252526;")
        
        # Content Tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.tabs)
```

- [ ] **Step 3: Create entry point script**
```python
# ui_app.py
from meeting_recorder.ui.main_window import MeetRecorderApp
from PyQt6.QtWidgets import QApplication
import sys

def main():
    app = QApplication(sys.argv)
    window = MeetRecorderApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify UI launches**
Run: `uv run python ui_app.py`

- [ ] **Step 5: Commit**
`git add . && git commit -m "feat(ui): setup PyQt6 boilerplate and main window"`

---

### Task 2: Session Manager & Sidebar List

**Files:**
- Create: `meeting_recorder/ui/models.py`
- Create: `meeting_recorder/ui/sidebar.py`

- [ ] **Step 1: Implement Session Manager**
Create logic to scan `recordings/` folder and parse `transcript.json` / `summary.md` existence.

- [ ] **Step 2: Create Sidebar Widget**
Implement `QListWidget` with custom items displaying date/time and status icons (🟢/🟡).

- [ ] **Step 3: Connect Sidebar to Main Window**
Embed `SidebarWidget` into `MeetRecorderApp`.

- [ ] **Step 4: Commit**
`git commit -m "feat(ui): implement recording list sidebar with session discovery"`

---

### Task 3: Recording Control & Live Feed

**Files:**
- Create: `meeting_recorder/ui/recording_tab.py`
- Create: `meeting_recorder/ui/workers.py`

- [ ] **Step 1: Design Recording Layout**
Add VU Meters (progress bars), Timer, and Start/Stop buttons.

- [ ] **Step 2: Implement Recording Worker (QThread)**
Bridge PyQt signals to `WindowsCaptureEngine`.

- [ ] **Step 3: Implement Live Feed UI**
Add `QTextEdit` for Live Transcription and `QTableWidget` for Chunk Status.

- [ ] **Step 4: Commit**
`git commit -m "feat(ui): add recording control tab with live VU meters and transcription feed"`

---

### Task 4: History Viewer & Interactive Playback

**Files:**
- Create: `meeting_recorder/ui/history_tab.py`
- Create: `meeting_recorder/ui/player_bar.py`

- [ ] **Step 1: Summary & Transcript Viewer**
Use `QTextBrowser` for Summary (Markdown) and a custom list for Transcript segments.

- [ ] **Step 2: Multimedia Integration**
Implement `QMediaPlayer` to play the concatenated audio of a session.

- [ ] **Step 3: Interactive Sync**
Implement "Click-to-Seek" (clicking transcript jumps audio) and "Highlight-on-Play" (audio playback highlights transcript).

- [ ] **Step 4: Commit**
`git commit -m "feat(ui): implement interactive playback with synced transcript highlighting"`

---

### Task 5: System Tray, Settings, and Final Integration

**Files:**
- Create: `meeting_recorder/ui/settings_tab.py`
- Modify: `meeting_recorder/ui/main_window.py`

- [ ] **Step 1: System Tray Icon**
Implement `QSystemTrayIcon` with context menu (Start/Stop, Open, Exit).

- [ ] **Step 2: Settings Panel**
Add fields for API Keys, default models, and audio device selection.

- [ ] **Step 3: AI Re-run Actions**
Add "Re-generate Summary" and "Re-transcribe" buttons to the History tab.

- [ ] **Step 4: Final Polish & Verification**
Verify all cross-tab interactions and resource cleanup.

- [ ] **Step 5: Commit**
`git commit -m "feat(ui): add system tray, settings, and AI re-run actions"`
