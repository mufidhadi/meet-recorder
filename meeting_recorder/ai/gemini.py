import google.generativeai as genai
from meeting_recorder.ai.summarizer import Summarizer
from meeting_recorder.data.summary import MeetingSummary

class GeminiSummarizer(Summarizer):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def summarize(self, transcript_text: str) -> MeetingSummary:
        prompt = f"""
        Tolong buatkan ringkasan rapat yang sangat profesional dari transkrip berikut.
        Gunakan format Markdown dengan struktur:
        1. Judul Rapat (Berdasarkan konteks)
        2. Peserta (Jika terdeteksi)
        3. Agenda Utama
        4. Poin-Poin Diskusi & Keputusan
        5. Action Items (Siapa melakukan apa)
        
        Transkrip:
        {transcript_text}
        """
        
        # genai SDK for Python is currently blocking/synchronous in its main call.
        # For MVP we use it as is, but in a production async app we'd wrap it in to_thread.
        response = self.model.generate_content(prompt)
        
        # Simple extraction for title - usually the first line of the response or context-based
        title = "Ringkasan Rapat" # Default
        lines = response.text.strip().split('\n')
        if lines and lines[0].startswith('# '):
            title = lines[0].replace('# ', '')
            
        return MeetingSummary(
            title=title,
            raw_markdown=response.text
        )
