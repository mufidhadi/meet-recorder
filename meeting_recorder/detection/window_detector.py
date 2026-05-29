import platform
import re
from dataclasses import dataclass

MEETING_WINDOW_PATTERNS = [
    # (regex_pattern, score, app_name)
    (r"zoom meeting",            35, "Zoom"),
    (r"zoom - pro account",      15, "Zoom"),
    (r"google meet",             35, "Google Meet"),
    (r"meet\.google\.com",       30, "Google Meet"),
    (r"microsoft teams.*meeting",35, "Microsoft Teams"),
    (r"teams.*call",             30, "Microsoft Teams"),
    (r"webex.*meeting",          35, "Webex"),
    (r"discord.*voice",          25, "Discord"),
    (r"slack.*call",             25, "Slack"),
    (r"whereby",                 30, "Whereby"),
]

@dataclass
class WindowMatch:
    window_title: str
    app_name: str
    score: int

class WindowDetector:
    def detect(self) -> list[WindowMatch]:
        titles = self._get_all_window_titles()
        matches = []
        
        for title in titles:
            title_lower = title.lower()
            for pattern, score, app_name in MEETING_WINDOW_PATTERNS:
                if re.search(pattern, title_lower):
                    matches.append(WindowMatch(
                        window_title=title,
                        app_name=app_name,
                        score=score,
                    ))
                    break  
        return matches

    def _get_all_window_titles(self) -> list[str]:
        system = platform.system()
        if system == "Windows":
            return self._get_windows_titles()
        return [] # Other platforms placeholder

    def _get_windows_titles(self) -> list[str]:
        import win32gui
        titles = []
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    titles.append(title)
        win32gui.EnumWindows(callback, None)
        return titles
