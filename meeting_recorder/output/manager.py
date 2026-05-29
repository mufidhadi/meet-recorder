import os
import json
import wave
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List
from meeting_recorder.data.transcription import TranscriptSegment

class OutputManager:
    def __init__(self, base_dir: str = "./recordings"):
        self.base_dir = Path(base_dir)
        self.session_dir = None

    def start_session(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.base_dir / timestamp
        self.session_dir.mkdir(parents=True, exist_ok=True)
        return self.session_dir

    def save_transcript(self, segments: List[TranscriptSegment], full_text_with_timestamps: str):
        if not self.session_dir:
            raise RuntimeError("Session not started.")
            
        # Save JSON
        json_path = self.session_dir / "transcript.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in segments], f, indent=2, ensure_ascii=False)
            
        # Save TXT
        txt_path = self.session_dir / "transcript.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text_with_timestamps)

    def save_audio(self, data: np.ndarray, sample_rate: int):
        if not self.session_dir:
            raise RuntimeError("Session not started.")
            
        path = self.session_dir / "session_full.wav"
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data.tobytes())

    def save_summary(self, markdown_content: str):
        if not self.session_dir:
            raise RuntimeError("Session not started.")
            
        path = self.session_dir / "summary.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    def save_audio_chunk(self, index: int, wav_bytes: bytes):
        """Optional: Save raw chunks for debugging."""
        if not self.session_dir:
            return
        
        chunks_dir = self.session_dir / "chunks"
        chunks_dir.mkdir(exist_ok=True)
        path = chunks_dir / f"chunk_{index:03d}.wav"
        with open(path, "wb") as f:
            f.write(wav_bytes)
