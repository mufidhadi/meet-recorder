from abc import ABC, abstractmethod
from meeting_recorder.data.transcription import TranscriptResult

class Transcriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        pass
