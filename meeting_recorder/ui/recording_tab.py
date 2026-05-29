from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QProgressBar, QTextEdit, QTableWidget, QHeaderView, QTableWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal

class RecordingTab(QWidget):
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Timer
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 48px; font-family: 'Consolas'; color: #4CAF50;")
        layout.addWidget(self.timer_label)
        
        # VU Meters
        vu_layout = QVBoxLayout()
        
        # System VU
        sys_label_layout = QHBoxLayout()
        sys_label_layout.addWidget(QLabel("System Audio:"))
        self.sys_vu = QProgressBar()
        self.sys_vu.setTextVisible(False)
        self.sys_vu.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                background: #252526;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.sys_vu.setRange(0, 100)
        vu_layout.addLayout(sys_label_layout)
        vu_layout.addWidget(self.sys_vu)
        
        # Mic VU
        mic_label_layout = QHBoxLayout()
        mic_label_layout.addWidget(QLabel("Microphone:"))
        self.mic_vu = QProgressBar()
        self.mic_vu.setTextVisible(False)
        self.mic_vu.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                background: #252526;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.mic_vu.setRange(0, 100)
        vu_layout.addLayout(mic_label_layout)
        vu_layout.addWidget(self.mic_vu)
        
        layout.addLayout(vu_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Recording")
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.start_button.clicked.connect(self._on_start_clicked)
        
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #E81123;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        
        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.stop_button)
        layout.addLayout(btn_layout)
        
        # Live Transcription
        layout.addWidget(QLabel("Live Transcription:"))
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setStyleSheet("background-color: #1E1E1E; border: 1px solid #333;")
        layout.addWidget(self.transcription_text)
        
        # Chunk Status
        layout.addWidget(QLabel("Chunk Processing Status:"))
        self.chunk_table = QTableWidget(0, 2)
        self.chunk_table.setHorizontalHeaderLabels(["Timestamp", "Status"])
        self.chunk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.chunk_table.setStyleSheet("background-color: #1E1E1E; border: 1px solid #333;")
        layout.addWidget(self.chunk_table)

    def _on_start_clicked(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.start_requested.emit()

    def _on_stop_clicked(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_requested.emit()

    def update_vu_meters(self, sys: float, mic: float):
        self.sys_vu.setValue(int(sys * 100))
        self.mic_vu.setValue(int(mic * 100))

    def update_timer(self, time_str: str):
        self.timer_label.setText(time_str)

    def add_transcription(self, data: dict):
        text = data.get("text", "")
        if text:
            self.transcription_text.append(text)

    def add_chunk(self, status: str):
        row = self.chunk_table.rowCount()
        self.chunk_table.insertRow(row)
        self.chunk_table.setItem(row, 0, QTableWidgetItem(self.timer_label.text()))
        self.chunk_table.setItem(row, 1, QTableWidgetItem(status))
        self.chunk_table.scrollToBottom()

