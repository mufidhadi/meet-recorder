# UI Refactor and Unit Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor MeetRecorderApp UI for better maintainability and design compliance, and establish UI unit testing.

**Architecture:** Move UI initialization to a dedicated private method and use styling constants for DESIGN.md compliance. Use `pytest-qt` for headless UI testing.

**Tech Stack:** Python, PyQt6, pytest, pytest-qt, uv.

---

### Task 1: Setup Testing Environment

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pytest-qt to dev dependencies**

Run: `uv add --dev pytest-qt`

- [ ] **Step 2: Sync dependencies**

Run: `uv sync`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pytest-qt to dev dependencies"
```

### Task 2: Refactor UI and Apply Design Constants

**Files:**
- Modify: `meeting_recorder/ui/main_window.py`

- [ ] **Step 1: Refactor MeetRecorderApp and apply styles**

```python
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QTabWidget

# Design Constants
APP_BG = "#1E1E1E"
SIDEBAR_BG = "#252526"
BORDER_RADIUS = "8px"

class MeetRecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Meet-Recorder")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"background-color: {APP_BG}; color: white;")
        
        # Central Widget & Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QHBoxLayout(central)
        
        # Sidebar placeholder
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet(f"""
            background-color: {SIDEBAR_BG};
            border-radius: {BORDER_RADIUS};
        """)
        
        # Content Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #333333;
                border-radius: {BORDER_RADIUS};
            }}
            QTabBar::tab {{
                background: {SIDEBAR_BG};
                border-radius: {BORDER_RADIUS};
                padding: 8px;
                margin: 2px;
            }}
            QTabBar::tab:selected {{
                background: #333333;
            }}
        """)
        
        # Add placeholder tabs
        self.tabs.addTab(QWidget(), "History")
        self.tabs.addTab(QWidget(), "Recording Control")
        
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.tabs)
```

- [ ] **Step 2: Verify code runs (no import errors)**

Run: `uv run python -c "from meeting_recorder.ui.main_window import MeetRecorderApp"`

- [ ] **Step 3: Commit**

```bash
git add meeting_recorder/ui/main_window.py
git commit -m "refactor: move UI setup to _init_ui and apply DESIGN.md styles"
```

### Task 3: Create UI Unit Test

**Files:**
- Create: `tests/unit/test_ui_main.py`

- [ ] **Step 1: Write UI initialization test**

```python
import pytest
from meeting_recorder.ui.main_window import MeetRecorderApp

def test_main_window_initialization(qtbot):
    """Verify that the main window and its core components initialize correctly."""
    window = MeetRecorderApp()
    qtbot.addWidget(window)
    
    assert window.windowTitle() == "Meet-Recorder"
    assert window.sidebar is not None
    assert window.tabs.count() == 2
    assert window.tabs.tabText(0) == "History"
    assert window.tabs.tabText(1) == "Recording Control"
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/unit/test_ui_main.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_ui_main.py
git commit -m "test: add basic UI initialization test"
```
