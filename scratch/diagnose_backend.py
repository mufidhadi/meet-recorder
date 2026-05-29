import asyncio
import os
import sys
from meeting_recorder.config.settings import Settings
from meeting_recorder.capture.windows import WindowsCaptureEngine
from meeting_recorder.processing.buffer import RingBuffer
from meeting_recorder.processing.chunker import AudioChunker
from meeting_recorder.transcription.gemini_transcriber import GeminiTranscriber
from meeting_recorder.transcription.local_hf import LocalHFTranscriber
import numpy as np

async def test_backend():
    print("Testing backend components...")
    settings = Settings()
    
    # 1. Test Capture Engine Discovery
    print("\n1. Testing Device Discovery...")
    try:
        from meeting_recorder.capture.windows import WindowsCaptureEngine
        engine = WindowsCaptureEngine(settings.audio, lambda x: None)
        loopback = engine._get_default_loopback_device()
        mic = engine._get_default_mic_device()
        print(f"Loopback Device: {loopback['name'] if loopback else 'NOT FOUND'}")
        print(f"Mic Device: {mic['name'] if mic else 'NOT FOUND'}")
    except Exception as e:
        print(f"Device discovery failed: {e}")

    # 2. Test Chunker & Buffer
    print("\n2. Testing Buffer & Chunker...")
    buffer = RingBuffer(maxsize_seconds=10, sample_rate=16000)
    data = np.zeros(16000, dtype=np.int16)
    buffer.push(data)
    print(f"Buffer size: {buffer.size} samples ({buffer.available_seconds}s)")
    
    # 3. Test Transcriber Initialization
    print("\n3. Testing Transcriber Initialization...")
    try:
        if settings.transcription_engine == "gemini":
            print(f"Initializing Gemini ({settings.gemini_model_id})...")
            if not settings.gemini_api_key:
                print("WARNING: GEMINI_API_KEY is missing!")
            t = GeminiTranscriber(api_key=settings.gemini_api_key, model_name=settings.gemini_model_id)
        else:
            print(f"Initializing Local Whisper ({settings.local_model_id})... This may take time.")
            t = LocalHFTranscriber(model_id=settings.local_model_id)
        print("Transcriber initialized successfully.")
    except Exception as e:
        print(f"Transcriber initialization failed: {e}")

    print("\nBackend diagnostic complete.")

if __name__ == "__main__":
    asyncio.run(test_backend())
