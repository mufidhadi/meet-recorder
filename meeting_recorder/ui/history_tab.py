import json
import os
import bisect
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextBrowser, QScrollArea, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from meeting_recorder.ui.models import RecordingSession

# Design Constants
TRANSCRIPT_HIGHLIGHT = "#FFEB3B33" # Yellow with transparency
TRANSCRIPT_NORMAL = "transparent"
BORDER_RADIUS = "8px"

class TranscriptSegmentWidget(QFrame):
    clicked = pyqtSignal(int) # ms

    def __init__(self, start_ms: int, text: str, parent=None):
        super().__init__(parent)
        self.start_ms = start_ms
        self.text = text
        self._is_highlighted = False
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"background-color: {TRANSCRIPT_NORMAL}; border-radius: 4px; padding: 5px;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Timestamp
        h = self.start_ms // 3600000
        m = (self.start_ms % 3600000) // 60000
        s = (self.start_ms % 60000) // 1000
        time_str = f"[{h:02d}:{m:02d}:{s:02d}]"
        
        self.time_label = QLabel(time_str)
        self.time_label.setStyleSheet("color: #888888; font-family: 'Consolas'; font-size: 12px;")
        self.time_label.setFixedWidth(80)
        layout.addWidget(self.time_label)
        
        # Text
        self.text_label = QLabel(self.text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
        layout.addWidget(self.text_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.start_ms)
        super().mousePressEvent(event)

    def set_highlight(self, highlighted: bool):
        if self._is_highlighted == highlighted:
            return
        self._is_highlighted = highlighted
        if highlighted:
            self.setStyleSheet(f"background-color: {TRANSCRIPT_HIGHLIGHT}; border-radius: 4px; padding: 5px;")
        else:
            self.setStyleSheet(f"background-color: {TRANSCRIPT_NORMAL}; border-radius: 4px; padding: 5px;")

class HistoryTab(QWidget):
    seek_requested = pyqtSignal(int) # ms
    re_transcribe_requested = pyqtSignal(RecordingSession)
    re_summarize_requested = pyqtSignal(RecordingSession)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segment_widgets = []
        self._segment_starts = []
        self._last_highlighted_index = -1
        self._active_session = None
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # AI Actions Section
        self.actions_layout = QHBoxLayout()
        self.re_transcribe_btn = QPushButton("Re-transcribe")
        self.re_summarize_btn = QPushButton("Regenerate Summary")
        
        btn_style = """
            QPushButton {
                background-color: #333333;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 5px 10px;
                color: #E1E1E1;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """
        self.re_transcribe_btn.setStyleSheet(btn_style)
        self.re_summarize_btn.setStyleSheet(btn_style)
        
        self.re_transcribe_btn.clicked.connect(self._on_re_transcribe)
        self.re_summarize_btn.clicked.connect(self._on_re_summarize)
        
        self.actions_layout.addWidget(self.re_transcribe_btn)
        self.actions_layout.addWidget(self.re_summarize_btn)
        self.actions_layout.addStretch()
        self.layout.addLayout(self.actions_layout)
        
        # Summary Section
        self.layout.addWidget(QLabel("AI Summary:"))
        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(True)
        self.summary_view.setStyleSheet(f"""
            QTextBrowser {{
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: {BORDER_RADIUS};
                padding: 10px;
                color: #E1E1E1;
            }}
        """)
        self.summary_view.setMaximumHeight(200)
        self.layout.addWidget(self.summary_view)
        
        # Transcript Section
        self.layout.addWidget(QLabel("Transcript:"))
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: {BORDER_RADIUS};
            }}
            QScrollBar:vertical {{
                background: #2D2D2D;
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background: #3F3F3F;
                min-height: 20px;
                border-radius: 6px;
            }}
        """)
        
        self.transcript_container = QWidget()
        self.transcript_container.setStyleSheet("background-color: transparent;")
        self.transcript_layout = QVBoxLayout(self.transcript_container)
        self.transcript_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.transcript_layout.setContentsMargins(5, 5, 5, 5)
        self.transcript_layout.setSpacing(2)
        
        self.scroll_area.setWidget(self.transcript_container)
        self.layout.addWidget(self.scroll_area)

    def _on_re_transcribe(self):
        if self._active_session:
            self.re_transcribe_requested.emit(self._active_session)

    def _on_re_summarize(self):
        if self._active_session:
            self.re_summarize_requested.emit(self._active_session)

    def load_session(self, session: RecordingSession):
        self._active_session = session
        
        # Reset scroll position
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # Load Summary
        summary_path = os.path.join(session.path, "summary.md")
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                md_content = f.read()
                # Basic Markdown rendering by QTextBrowser (it supports some HTML subset)
                self.summary_view.setMarkdown(md_content)
        else:
            self.summary_view.setText("No summary available for this session.")

        # Load Transcript
        self._clear_transcript()
        transcript_path = os.path.join(session.path, "transcript.json")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Handle both list and dict formats
                    if isinstance(data, list):
                        segments = data
                    elif isinstance(data, dict) and "segments" in data:
                        segments = data["segments"]
                    else:
                        raise ValueError("Transcript format invalid")
                        
                    for seg in segments:
                        if not isinstance(seg, dict) or ("start" not in seg and "timestamp" not in seg) or "text" not in seg:
                            continue
                        
                        start_val = seg.get("start") if seg.get("start") is not None else seg.get("timestamp")
                        start_ms = int(start_val * 1000)
                        widget = TranscriptSegmentWidget(start_ms, seg["text"])
                        widget.clicked.connect(self.seek_requested.emit)
                        self.transcript_layout.addWidget(widget)
                        self._segment_widgets.append(widget)
                        self._segment_starts.append(start_ms)
            except Exception as e:
                self.transcript_layout.addWidget(QLabel(f"Error loading transcript: {e}"))
        else:
            self.transcript_layout.addWidget(QLabel("No transcript available."))

    def highlight_at_time(self, ms: int):
        """Highlights the segment corresponding to the given time in ms."""
        if not self._segment_starts:
            return

        # Find the segment using binary search O(log N)
        idx = bisect.bisect_right(self._segment_starts, ms) - 1
        idx = max(0, idx)

        if idx == self._last_highlighted_index:
            return

        # Unhighlight previous
        if self._last_highlighted_index != -1 and self._last_highlighted_index < len(self._segment_widgets):
            self._segment_widgets[self._last_highlighted_index].set_highlight(False)

        # Highlight new
        if idx < len(self._segment_widgets):
            active_widget = self._segment_widgets[idx]
            active_widget.set_highlight(True)
            self._last_highlighted_index = idx
            
            # Scroll to active widget if needed, but only if user is not manually scrolling
            if not self.scroll_area.verticalScrollBar().isSliderDown():
                self.scroll_area.ensureWidgetVisible(active_widget)

    def _clear_transcript(self):
        for widget in self._segment_widgets:
            self.transcript_layout.removeWidget(widget)
            widget.deleteLater()
        self._segment_widgets = []
        self._segment_starts = []
        self._last_highlighted_index = -1
