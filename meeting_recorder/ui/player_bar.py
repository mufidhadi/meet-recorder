import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class PlayerBar(QWidget):
    position_changed = pyqtSignal(int)  # ms
    duration_changed = pyqtSignal(int)  # ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0) # Ensure volume is up
        self.player.setAudioOutput(self.audio_output)
        
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(60)
        self.setStyleSheet("""
            PlayerBar {
                background-color: #252526;
                border-top: 1px solid #333333;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        
        # Play/Pause
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_btn)
        
        # Time Label (Current)
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: #CCCCCC; font-family: 'Consolas';")
        layout.addWidget(self.current_time_label)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 4px;
                background: #444;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #0078D4;
                border: 1px solid #0078D4;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        layout.addWidget(self.slider)
        
        # Time Label (Total)
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: #CCCCCC; font-family: 'Consolas';")
        layout.addWidget(self.total_time_label)

    def load_audio(self, file_path: str):
        print(f"[PLAYER] Loading audio: {file_path}")
        # Force a stop and source clear to avoid being "stuck"
        self.player.stop()
        self.player.setSource(QUrl())
        
        if not file_path or not os.path.exists(file_path):
            print(f"[PLAYER] ERROR: File not found: {file_path}")
            return
        abs_path = os.path.abspath(file_path)
        self.player.setSource(QUrl.fromLocalFile(abs_path))
        self.play_btn.setText("▶")
        print("[PLAYER] Source set successfully.")

    def toggle_play(self):
        state = self.player.playbackState()
        print(f"[PLAYER] Toggle play requested. Current state: {state}")
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶")
            print("[PLAYER] Paused.")
        else:
            self.player.play()
            self.play_btn.setText("⏸")
            print("[PLAYER] Playing.")

    def set_position(self, ms: int):
        self.player.setPosition(ms)

    def cleanup(self):
        """Cleanup player resources."""
        self.player.stop()
        self.player.setSource(QUrl())

    def _on_position_changed(self, ms: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(ms)
        self.current_time_label.setText(self._format_time(ms))
        self.position_changed.emit(ms)

    def _on_duration_changed(self, ms: int):
        self.slider.setRange(0, ms)
        self.total_time_label.setText(self._format_time(ms))
        self.duration_changed.emit(ms)

    def _on_slider_moved(self, ms: int):
        self.player.setPosition(ms)

    def _format_time(self, ms: int) -> str:
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
