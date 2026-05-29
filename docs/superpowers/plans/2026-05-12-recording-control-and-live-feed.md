# Recording Control & Live Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the RecordingTab UI and integrate it into the main application.

**Architecture:** Create a new QWidget subclass `RecordingTab` that handles the recording UI, manages the `RecordingWorker`, and updates UI elements (timer, VU meters, transcription, chunk status) via signals.

**Tech Stack:** PyQt6, asyncio, numpy.

---

### Task 1: Research & Scaffolding

**Files:**
- Create: `meeting_recorder/ui/recording_tab.py`
- Modify: `meeting_recorder/ui/main_window.py`

- [ ] **Step 1: Check existing test failure**
Run: `uv run pytest tests/unit/test_ui_recording.py`
Expected: FAIL (ModuleNotFoundError: No module named 'meeting_recorder.ui.recording_tab')

- [ ] **Step 2: Create empty RecordingTab class**
```python
from PyQt6.QtWidgets import QWidget

class RecordingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
```

- [ ] **Step 3: Run test again**
Run: `uv run pytest tests/unit/test_ui_recording.py`
Expected: FAIL (AttributeError: 'RecordingTab' object has no attribute 'start_button')

---

### Task 2: Implement UI Layout

**Files:**
- Modify: `meeting_recorder/ui/recording_tab.py`

- [ ] **Step 1: Add basic UI components**
```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QProgressBar, QTextEdit, QTableWidget
)
from PyQt6.QtCore import Qt

class RecordingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Timer
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 48px; font-family: 'Consolas';")
        layout.addWidget(self.timer_label)
        
        # VU Meters
        vu_layout = QHBoxLayout()
        self.sys_vu = QProgressBar()
        self.sys_vu.setOrientation(Qt.Orientation.Horizontal)
        self.sys_vu.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        self.sys_vu.setRange(0, 100)
        
        self.mic_vu = QProgressBar()
        self.mic_vu.setOrientation(Qt.Orientation.Horizontal)
        self.mic_vu.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        self.mic_vu.setRange(0, 100)
        
        vu_layout.addWidget(QLabel("System:"))
        vu_layout.addWidget(self.sys_vu)
        vu_layout.addWidget(QLabel("Mic:"))
        vu_layout.addWidget(self.mic_vu)
        layout.addLayout(vu_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Recording")
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #E81123;")
        
        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.stop_button)
        layout.addLayout(btn_layout)
        
        # Live Transcription
        layout.addWidget(QLabel("Live Transcription:"))
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        layout.addWidget(self.transcription_text)
        
        # Chunk Status
        layout.addWidget(QLabel("Chunks:"))
        self.chunk_table = QTableWidget(0, 2)
        self.chunk_table.setHorizontalHeaderLabels(["Timestamp", "Status"])
        layout.addWidget(self.chunk_table)
```

- [ ] **Step 2: Run tests**
Run: `uv run pytest tests/unit/test_ui_recording.py`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add meeting_recorder/ui/recording_tab.py
git commit -m "feat(ui): add RecordingTab layout"
```

---

### Task 3: Integrate Logic & Signals

**Files:**
- Modify: `meeting_recorder/ui/recording_tab.py`

- [ ] **Step 1: Implement button toggling and signal slots**
```python
class RecordingTab(QWidget):
    # ... existing __init__ and _init_ui ...
    
    def _init_ui(self):
        # ...
        self.start_button.clicked.connect(self._on_start_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        # ...

    def _on_start_clicked(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        # In real usage, this would emit a signal to main_window to start the worker

    def _on_stop_clicked(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_vu_meters(self, sys: float, mic: float):
        self.sys_vu.setValue(int(sys * 100))
        self.mic_vu.setValue(int(mic * 100))

    def update_timer(self, time_str: str):
        self.timer_label.setText(time_str)

    def add_transcription(self, data: dict):
        text = data.get("text", "")
        self.transcription_text.append(text)

    def add_chunk(self, status: str):
        row = self.chunk_table.rowCount()
        self.chunk_table.insertRow(row)
        self.chunk_table.setItem(row, 0, QTableWidgetItem(self.timer_label.text()))
        self.chunk_table.setItem(row, 1, QTableWidgetItem(status))
```

- [ ] **Step 2: Run tests**
Run: `uv run pytest tests/unit/test_ui_recording.py`
Expected: PASS

---

### Task 4: Integration with Main Window

**Files:**
- Modify: `meeting_recorder/ui/main_window.py`

- [ ] **Step 1: Replace placeholder tab with RecordingTab**
```python
from meeting_recorder.ui.recording_tab import RecordingTab

class MeetRecorderApp(QMainWindow):
    # ...
    def _init_ui(self):
        # ...
        self.tabs.addTab(QWidget(), "History")
        self.recording_tab = RecordingTab()
        self.tabs.addTab(self.recording_tab, "Recording Control")
        # ...
```

- [ ] **Step 2: Verify application launch**
Run: `uv run python main.py` (optional, can't see it but can run it to check for crashes)
Or run `uv run pytest tests/unit/test_ui_main.py`

- [ ] **Step 3: Commit**
```bash
git add meeting_recorder/ui/recording_tab.py meeting_recorder/ui/main_window.py
git commit -m "feat(ui): integrate RecordingTab into main window"
```

---

### Task 5: Final Verification & Report

- [ ] **Step 1: Run all UI tests**
Run: `uv run pytest tests/unit/test_ui_main.py tests/unit/test_ui_recording.py`

- [ ] **Step 2: Create FINAL_REPORT_DUAL_AUDIO.md**
(Include requested sections: task name, history, tech stack, difficulties, lessons learned)

- [ ] **Step 3: Final Commit**
```bash
git add FINAL_REPORT_DUAL_AUDIO.md
git commit -m "docs: add final report for Task 3"
```
