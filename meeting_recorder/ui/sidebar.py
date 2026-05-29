from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush
from typing import List
from meeting_recorder.ui.models import RecordingSession

# Design Constants
SIDEBAR_BG = "#252526"
BORDER_RADIUS = "8px"
COLOR_GREEN = "#4CAF50"
COLOR_YELLOW = "#FFC107"
COLOR_GRAY = "#808080"

class SidebarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._icons = {}  # Cache for status icons
        self._init_ui()

    def _init_ui(self):
        self.setFixedWidth(250)
        self.setStyleSheet(f"""
            background-color: {SIDEBAR_BG};
            border-radius: {BORDER_RADIUS};
            color: white;
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.title = QLabel("Recent Sessions")
        self.title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        self.layout.addWidget(self.title)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background-color: #37373d;
            }}
            QListWidget::item:hover {{
                background-color: #2a2d2e;
            }}
        """)
        self.layout.addWidget(self.list_widget)

    def _get_status_icon(self, color_hex: str) -> QIcon:
        if color_hex in self._icons:
            return self._icons[color_hex]

        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 12, 12)
        painter.end()
        
        icon = QIcon(pixmap)
        self._icons[color_hex] = icon
        return icon

    def set_sessions(self, sessions: List[RecordingSession]):
        self.list_widget.clear()
        for session in sessions:
            item = QListWidgetItem(session.formatted_date)
            item.setData(Qt.ItemDataRole.UserRole, session)
            
            if session.has_transcript and session.has_summary:
                item.setIcon(self._get_status_icon(COLOR_GREEN))
            elif session.has_transcript:
                item.setIcon(self._get_status_icon(COLOR_YELLOW))
            else:
                item.setIcon(self._get_status_icon(COLOR_GRAY))
                
            self.list_widget.addItem(item)
