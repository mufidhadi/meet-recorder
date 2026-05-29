from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QMessageBox, QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt
from meeting_recorder.ui.sidebar import SidebarWidget
from meeting_recorder.ui.recording_tab import RecordingTab
from meeting_recorder.ui.history_tab import HistoryTab
from meeting_recorder.ui.settings_tab import SettingsTab
from meeting_recorder.ui.player_bar import PlayerBar
from meeting_recorder.ui.models import SessionManager, RecordingSession
import os
import numpy as np
from meeting_recorder.ui.workers import RecordingWorker, AISubagentWorker
from meeting_recorder.config.settings import Settings
from meeting_recorder.processing.buffer import RingBuffer
from meeting_recorder.output.manager import OutputManager
from meeting_recorder.ai.aggregator import TranscriptAggregator
from meeting_recorder.transcription.local_hf import LocalHFTranscriber
from meeting_recorder.transcription.gemini_transcriber import GeminiTranscriber

# Design Constants
APP_BG = "#1E1E1E"
SIDEBAR_BG = "#252526"
BORDER_RADIUS = "8px"

class MeetRecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.session_manager = SessionManager()
        self.output_manager = OutputManager(base_dir=self.settings.output_dir)
        self.aggregator = TranscriptAggregator()
        self.ring_buffer = RingBuffer(
            maxsize_seconds=600, 
            sample_rate=self.settings.audio.sample_rate
        )
        
        self.transcriber = self._init_transcriber()
        self.worker = None
        self.ai_worker = None
        
        self._init_ui()
        self._init_tray()
        self._load_sessions()

    def _init_transcriber(self):
        if self.settings.transcription_engine == "gemini":
            return GeminiTranscriber(
                api_key=self.settings.gemini_api_key,
                model_name=self.settings.gemini_model_id
            )
        else:
            return LocalHFTranscriber(model_id=self.settings.local_model_id)

    def _init_ui(self):
        self.setWindowTitle("Meet-Recorder")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"background-color: {APP_BG}; color: white;")
        
        # Central Widget & Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(10)
        
        self.main_layout = QHBoxLayout()
        outer_layout.addLayout(self.main_layout)
        
        # Sidebar
        self.sidebar = SidebarWidget()
        self.sidebar.list_widget.itemSelectionChanged.connect(self._load_selected_session)
        
        # Content Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #333333;
                border-radius: {BORDER_RADIUS};
            }}
            QTabBar::tab {{
                background: {SIDEBAR_BG};
                border-top-left-radius: {BORDER_RADIUS};
                border-top-right-radius: {BORDER_RADIUS};
                padding: 8px 15px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: #333333;
            }}
        """)
        
        # History Tab
        self.history_tab = HistoryTab()
        self.history_tab.re_transcribe_requested.connect(self._on_re_transcribe)
        self.history_tab.re_summarize_requested.connect(self._on_re_summarize)
        self.tabs.addTab(self.history_tab, "History")
        
        # Recording Tab
        self.recording_tab = RecordingTab()
        self.recording_tab.start_requested.connect(self._start_recording)
        self.recording_tab.stop_requested.connect(self._stop_recording)
        self.tabs.addTab(self.recording_tab, "Recording Control")

        # Settings Tab
        self.settings_tab = SettingsTab()
        self.settings_tab.settings_saved.connect(self._on_settings_saved)
        self.tabs.addTab(self.settings_tab, "Settings")
        
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.tabs)
        
        # Player Bar
        self.player_bar = PlayerBar()
        outer_layout.addWidget(self.player_bar)
        
        # Inter-component signals
        self.history_tab.seek_requested.connect(self.player_bar.set_position)
        self.player_bar.player.positionChanged.connect(self.history_tab.highlight_at_time)

    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        # Use a built-in icon for now
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay)
        self.tray_icon.setIcon(icon)
        
        tray_menu = QMenu()
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.showNormal)
        
        start_action = QAction("Start Recording", self)
        start_action.triggered.connect(self._start_recording)
        
        stop_action = QAction("Stop Recording", self)
        stop_action.triggered.connect(self._stop_recording)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._on_exit)
        
        tray_menu.addAction(open_action)
        tray_menu.addSeparator()
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()

    def _on_exit(self):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Recording in progress",
                "A recording is currently in progress. Stop recording and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            
            # Connect finish signal to actual quit
            self.worker.finished_recording.connect(self._graceful_quit)
            self._stop_recording()
            self.hide()
            return

        self._graceful_quit()

    def _graceful_quit(self):
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "Meet-Recorder",
                "Application is still running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()

    def _on_settings_saved(self):
        # Reload settings and transcriber
        self.settings = Settings()
        self.transcriber = self._init_transcriber()
        self.output_manager = OutputManager(base_dir=self.settings.output_dir)

    def _on_re_transcribe(self, session: RecordingSession):
        self._run_ai_task("re-transcribe", session)

    def _on_re_summarize(self, session: RecordingSession):
        self._run_ai_task("re-summarize", session)

    def _run_ai_task(self, task_type: str, session: RecordingSession):
        if self.ai_worker and self.ai_worker.isRunning():
            QMessageBox.warning(self, "Busy", "Another AI task is already running.")
            return
            
        self.ai_worker = AISubagentWorker(task_type, session, self.settings)
        self.ai_worker.finished.connect(lambda success, msg: self._on_ai_task_finished(success, msg, session))
        self.ai_worker.start()
        
        self.tray_icon.showMessage(
            "Meet-Recorder",
            f"Starting AI task: {task_type}",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _on_ai_task_finished(self, success: bool, message: str, session: RecordingSession):
        if success:
            self.tray_icon.showMessage(
                "Meet-Recorder",
                f"AI task completed successfully.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            # Refresh view if the finished session is the active one
            item = self.sidebar.list_widget.currentItem()
            if item:
                current_session = item.data(Qt.ItemDataRole.UserRole)
                if current_session.session_id == session.session_id:
                    self._load_selected_session()
        else:
            QMessageBox.critical(self, "AI Task Error", message)

    def _load_sessions(self):
        sessions = self.session_manager.get_sessions()
        self.sidebar.set_sessions(sessions)

    def _load_selected_session(self):
        item = self.sidebar.list_widget.currentItem()
        if not item:
            return
        
        session = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(session, RecordingSession):
            return
            
        self.history_tab.load_session(session)
        
        audio_path = os.path.join(session.path, "session_full.wav")
        if os.path.exists(audio_path):
            self.player_bar.load_audio(audio_path)
            # Switch to History tab
            self.tabs.setCurrentIndex(0)

    def _start_recording(self):
        print("[UI] Start recording requested.")
        # Ensure media player is cleaned up to avoid device conflicts
        self.player_bar.cleanup()
        
        # Reset aggregator and start output session
        self.aggregator = TranscriptAggregator()
        self.output_manager.start_session()
        print(f"[UI] Session started in: {self.output_manager.session_dir}")
        
        self.worker = RecordingWorker(
            config=self.settings.audio,
            settings=self.settings,
            output_manager=self.output_manager,
            ring_buffer=self.ring_buffer,
            transcriber=self.transcriber,
            aggregator=self.aggregator
        )
        
        # Connect signals
        self.worker.vu_levels.connect(self.recording_tab.update_vu_meters)
        self.worker.timer_tick.connect(self.recording_tab.update_timer)
        self.worker.transcription_received.connect(self.recording_tab.add_transcription)
        self.worker.chunk_ready.connect(self.recording_tab.add_chunk)
        self.worker.error_occurred.connect(self._handle_error)
        self.worker.finished_recording.connect(self._on_recording_finished)
        
        self.worker.start()
        print("[UI] RecordingWorker thread started.")

    def _stop_recording(self):
        print("[UI] Stop recording requested.")
        if self.worker:
            self.worker.stop()

    def _handle_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
        self._stop_recording()

    def _on_recording_finished(self):
        print("[UI] Recording finished. Saving data...")
        # Save results
        if self.output_manager.session_dir:
            full_text = self.aggregator.get_full_transcript()
            self.output_manager.save_transcript(self.aggregator.all_segments, full_text)
            
            # Save full audio
            if self.worker:
                audio_data = self.worker.get_audio_data()
                if len(audio_data) > 0:
                    self.output_manager.save_audio(audio_data, self.settings.audio.sample_rate)
            
            # Auto-trigger summary
            session_id = os.path.basename(self.output_manager.session_dir)
            session = RecordingSession(
                session_id=session_id,
                path=self.output_manager.session_dir,
                has_transcript=True,
                has_summary=False
            )
            print(f"[UI] Triggering auto-summary for session {session_id}")
            self._on_re_summarize(session)
            
            self._load_sessions() # Refresh history
