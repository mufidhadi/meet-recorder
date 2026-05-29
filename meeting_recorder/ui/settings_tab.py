from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QComboBox, QLabel, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
import os
from meeting_recorder.config.settings import Settings
from meeting_recorder.utils.paths import get_base_path

class SettingsTab(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(15)

        # Gemini API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.settings.gemini_api_key or "")
        self.api_key_input.setPlaceholderText("Enter your Gemini API Key")
        form_layout.addRow("Gemini API Key:", self.api_key_input)

        # Gemini Model ID
        self.gemini_model_input = QLineEdit()
        self.gemini_model_input.setText(self.settings.gemini_model_id)
        form_layout.addRow("Gemini Model ID:", self.gemini_model_input)

        # Local Model ID
        self.local_model_input = QLineEdit()
        self.local_model_input.setText(self.settings.local_model_id)
        form_layout.addRow("Local Model ID:", self.local_model_input)

        # Transcription Engine
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["local", "gemini"])
        self.engine_combo.setCurrentText(self.settings.transcription_engine)
        form_layout.addRow("Default Engine:", self.engine_combo)

        layout.addWidget(form_frame)

        # Save Button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        layout.addWidget(self.save_btn)
        
        layout.addStretch()

    def _save_settings(self):
        api_key = self.api_key_input.text().strip()
        gemini_model = self.gemini_model_input.text().strip()
        local_model = self.local_model_input.text().strip()
        engine = self.engine_combo.currentText()

        # Update .env file
        try:
            env_path = os.path.join(get_base_path(), ".env")
            lines = []
            found_keys = set()
            
            new_values = {
                "GEMINI_API_KEY": api_key,
                "GEMINI_MODEL_ID": gemini_model,
                "LOCAL_MODEL_ID": local_model,
                "TRANSCRIPTION_ENGINE": engine
            }

            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if "=" in stripped and not stripped.startswith("#"):
                            # Robust parsing: strip both key and value
                            parts = stripped.split("=", 1)
                            key = parts[0].strip()
                            if key in new_values:
                                lines.append(f"{key}={new_values[key]}\n")
                                found_keys.add(key)
                            else:
                                lines.append(line)
                        else:
                            lines.append(line)
            
            # Add keys that weren't in the file
            for key, val in new_values.items():
                if key not in found_keys:
                    if lines and not lines[-1].endswith("\n"):
                        lines.append("\n")
                    lines.append(f"{key}={val}\n")

            with open(env_path, "w") as f:
                f.writelines(lines)

            QMessageBox.information(self, "Success", "Settings saved successfully to .env")
            self.settings_saved.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
