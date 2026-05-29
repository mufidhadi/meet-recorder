import sys
from PyQt6.QtWidgets import QApplication
from meeting_recorder.ui.main_window import MeetRecorderApp

def main():
    app = QApplication(sys.argv)
    window = MeetRecorderApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
