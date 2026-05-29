import io
import soundfile as sf
import numpy as np
from transformers import pipeline
from meeting_recorder.transcription.engine import Transcriber
from meeting_recorder.data.transcription import TranscriptResult, TranscriptSegment

class LocalHFTranscriber(Transcriber):
    def __init__(self, model_id: str):
        # Initialize pipeline. Will download model on first run.
        # This pipeline works for whisper models, and some others supported by HF ASR.
        import torch
        import os
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Ensure models directory exists
        os.makedirs("./models", exist_ok=True)
        
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model_id,
            device=device,
            model_kwargs={"cache_dir": "./models"} 
        )

    async def transcribe(self, audio_bytes: bytes) -> TranscriptResult:
        print(f"[LOCAL-AI] Processing {len(audio_bytes)} bytes...")
        # Transformers pipeline usually expects a numpy array or file path
        # Convert WAV bytes to numpy array
        audio_file = io.BytesIO(audio_bytes)
        data, samplerate = sf.read(audio_file)
        
        # If stereo, convert to mono
        if len(data.shape) > 1:
            data = data.mean(axis=1)

        # Ensure float32 for model inference
        data = data.astype(np.float32)

        # Run inference synchronously (MVP: wrapped in async def for interface compatibility)
        print("[LOCAL-AI] Running inference...")
        result = self.pipe(data)
        
        # HF ASR pipelines sometimes return list of dicts, sometimes dict
        if isinstance(result, list):
            text = " ".join([r.get("text", "").strip() for r in result])
        else:
            text = result.get("text", "").strip()
        
        print(f"[LOCAL-AI] Inference SUCCESS: {len(text)} characters.")
        return TranscriptResult(
            segments=[TranscriptSegment(start=0.0, end=30.0, text=text)],
            full_text=text
        )
