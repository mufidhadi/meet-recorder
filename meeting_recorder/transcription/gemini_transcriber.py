import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from meeting_recorder.transcription.engine import Transcriber
from meeting_recorder.data.transcription import TranscriptResult, TranscriptSegment

class GeminiTranscriber(Transcriber):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception), # Catch-all for API errors including 429
        reraise=True
    )
    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        """Transcribe audio bytes using Gemini 1.5 Flash."""
        print(f"[GEMINI] Sending {len(audio_bytes)} bytes to API...")
        # Gemini can accept bytes directly with mime_type
        response = self.model.generate_content([
            "Tolong buatkan transkrip dari audio ini secara verbatim (kata per kata). Jangan tambahkan komentar apapun, cukup transkripnya saja.",
            {"mime_type": "audio/wav", "data": audio_bytes}
        ])
        
        text = response.text.strip()
        print(f"[GEMINI] Received {len(text)} characters.")
        # Since we are doing 30s chunks, we map this text to a 30s segment for the aggregator
        return TranscriptResult(
            segments=[TranscriptSegment(start=0.0, end=30.0, text=text)],
            full_text=text
        )
