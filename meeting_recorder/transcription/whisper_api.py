import io
from openai import AsyncOpenAI
from meeting_recorder.transcription.engine import Transcriber
from meeting_recorder.data.transcription import TranscriptResult, TranscriptSegment

class WhisperAPITranscriber(Transcriber):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        # Create a file-like object with a name so Whisper API knows the format
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        response = await self.client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="verbose_json"
        )
        
        segments = []
        if hasattr(response, 'segments'):
            for s in response.segments:
                segments.append(TranscriptSegment(
                    start=s['start'],
                    end=s['end'],
                    text=s['text'].strip()
                ))
        
        return TranscriptResult(
            segments=segments,
            full_text=response.text.strip()
        )
