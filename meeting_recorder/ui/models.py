from dataclasses import dataclass
from pathlib import Path
from typing import List
from datetime import datetime

TRANSCRIPT_FILENAME = "transcript.json"
SUMMARY_FILENAME = "summary.md"

@dataclass
class RecordingSession:
    session_id: str
    path: str
    has_transcript: bool
    has_summary: bool

    @property
    def formatted_date(self) -> str:
        try:
            dt = datetime.strptime(self.session_id, "%Y%m%d_%H%M%S")
            return dt.strftime("%d %b %Y, %H:%M")
        except ValueError:
            return self.session_id

class SessionManager:
    def __init__(self, base_path: str = "recordings"):
        self.base_path = Path(base_path)

    def get_sessions(self) -> List[RecordingSession]:
        if not self.base_path.exists():
            return []
        
        sessions = []
        for item in self.base_path.iterdir():
            if item.is_dir():
                # Expected format: YYYYMMDD_HHMMSS
                # We can add more validation here if needed, but for now we follow the plan.
                has_transcript = (item / TRANSCRIPT_FILENAME).exists()
                has_summary = (item / SUMMARY_FILENAME).exists()
                
                sessions.append(RecordingSession(
                    session_id=item.name,
                    path=str(item),
                    has_transcript=has_transcript,
                    has_summary=has_summary
                ))
        
        # Sort by session_id (which is date-based) descending
        sessions.sort(key=lambda s: s.session_id, reverse=True)
        return sessions
