from abc import ABC, abstractmethod
from meeting_recorder.data.summary import MeetingSummary

class Summarizer(ABC):
    @abstractmethod
    async def summarize(self, transcript_text: str) -> MeetingSummary:
        pass
