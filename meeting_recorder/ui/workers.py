import time
import asyncio
import threading
from typing import Callable, Any
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
import numpy as np

from meeting_recorder.data.audio import AudioConfig
from meeting_recorder.capture.windows import WindowsCaptureEngine
from meeting_recorder.processing.chunker import AudioChunker
from meeting_recorder.data.transcription import TranscriptResult
from meeting_recorder.ui.models import RecordingSession, TRANSCRIPT_FILENAME, SUMMARY_FILENAME
from meeting_recorder.ai.gemini import GeminiSummarizer
from meeting_recorder.transcription.gemini_transcriber import GeminiTranscriber
from meeting_recorder.transcription.local_hf import LocalHFTranscriber
import os
import json
import asyncio
import soundfile as sf

class RecordingWorker(QThread):
    vu_levels = pyqtSignal(float, float)
    timer_tick = pyqtSignal(str)
    transcription_received = pyqtSignal(dict)
    chunk_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished_recording = pyqtSignal()

    def __init__(
        self,
        config: AudioConfig,
        settings: Any,
        output_manager: Any,
        ring_buffer: Any,
        transcriber: Any,
        aggregator: Any,
        engine_class: Any = WindowsCaptureEngine,
        chunker_class: Any = AudioChunker,
        parent=None
    ):
        super().__init__(parent)
        self.config = config
        self.settings = settings
        self.output_manager = output_manager
        self.ring_buffer = ring_buffer
        self.transcriber = transcriber
        self.aggregator = aggregator
        self.engine_class = engine_class
        self.chunker_class = chunker_class
        
        self.is_recording = False
        self.start_time = 0
        self.elapsed_s = 0
        self._all_audio = []
        
        self.engine = None
        self.chunker = None
        self.timer = None
        
        self._loop = None
        self._loop_thread = None

    def _on_vu_levels(self, loopback: float, mic: float):
        self.vu_levels.emit(loopback, mic)

    def _on_timer_tick(self):
        self.elapsed_s = int(time.time() - self.start_time)
        h = self.elapsed_s // 3600
        m = (self.elapsed_s % 3600) // 60
        s = self.elapsed_s % 60
        self.timer_tick.emit(f"{h:02d}:{m:02d}:{s:02d}")

    def run(self):
        print(f"RecordingWorker: starting in thread {threading.get_ident()}")
        try:
            # Setup asyncio event loop in a separate thread
            self._loop = asyncio.new_event_loop()
            self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self._loop_thread.start()
            print("RecordingWorker: asyncio loop thread started")

            self.start_time = time.time()
            self.is_recording = True
            
            # Setup engine
            def combined_callback(data):
                self.ring_buffer.push(data)
                self._all_audio.append(data.copy())

            print("RecordingWorker: initializing engine...")
            self.engine = self.engine_class(
                config=self.config,
                callback=combined_callback,
                vu_callback=self._on_vu_levels
            )
            
            # Setup chunker
            print("RecordingWorker: initializing chunker...")
            self.chunker = self.chunker_class(
                ring_buffer=self.ring_buffer,
                chunk_duration_s=self.settings.chunk_duration,
                on_chunk_callback=self._on_chunk_ready
            )
            
            # Start everything
            print("RecordingWorker: starting engine and chunker...")
            self.engine.start()
            self.chunker.start()
            
            # Timer for UI
            print("RecordingWorker: starting UI timer...")
            self.timer = QTimer()
            self.timer.timeout.connect(self._on_timer_tick)
            self.timer.start(1000)
            
            print("RecordingWorker: entering event loop")
            self.exec() # QThread event loop
            print("RecordingWorker: event loop exited")
            
        except Exception as e:
            print(f"RecordingWorker: ERROR: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.cleanup()

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_chunk_ready(self, wav_bytes: bytes, silent: bool):
        if not self.is_recording:
            return

        if silent:
            return
        
        self.chunk_ready.emit(f"Chunk at {self.elapsed_s}s")
        
        # Dispatch transcription task to the asyncio loop thread
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._transcribe_chunk(wav_bytes), 
                self._loop
            )

    async def _transcribe_chunk(self, wav_bytes: bytes):
        try:
            print(f"[WORKER] Transcription starting for chunk at {self.elapsed_s}s...")
            result = await self.transcriber.transcribe(wav_bytes)
            print(f"[WORKER] Transcription SUCCESS: {result.full_text[:50]}...")
            
            # Use chunk duration from settings
            offset = max(0, self.elapsed_s - self.settings.chunk_duration)
            self.aggregator.add_result(result, offset)
            
            self.transcription_received.emit({
                "text": result.full_text,
                "timestamp": self.elapsed_s
            })
        except Exception as e:
            print(f"[WORKER] Transcription ERROR: {e}")
            self.error_occurred.emit(f"Transcription error: {e}")

    def stop(self):
        print("[WORKER] Stop requested.")
        self.is_recording = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.quit()

    def get_audio_data(self) -> np.ndarray:
        if not self._all_audio:
            return np.array([], dtype=np.int16)
        return np.concatenate(self._all_audio)

    def cleanup(self):
        if self.timer:
            self.timer.stop()
        if self.chunker:
            self.chunker.stop()
        if self.engine:
            self.engine.stop()
        
        if self._loop_thread:
            self._loop_thread.join(timeout=2.0)
            
        self.finished_recording.emit()

class AISubagentWorker(QThread):
    finished = pyqtSignal(bool, str) # success, message

    def __init__(self, task_type: str, session: RecordingSession, settings: Any, parent=None):
        super().__init__(parent)
        self.task_type = task_type
        self.session = session
        self.settings = settings

    def run(self):
        print(f"[AI-WORKER] Task {self.task_type} starting for session {self.session.session_id}")
        try:
            if self.task_type == "re-transcribe":
                asyncio.run(self._run_transcription())
            elif self.task_type == "re-summarize":
                asyncio.run(self._run_summarization())
            print(f"[AI-WORKER] Task {self.task_type} SUCCESS")
            self.finished.emit(True, f"Task {self.task_type} completed.")
        except Exception as e:
            print(f"[AI-WORKER] Task {self.task_type} ERROR: {e}")
            self.finished.emit(False, str(e))

    async def _run_transcription(self):
        abs_session_path = os.path.abspath(self.session.path)
        audio_path = os.path.join(abs_session_path, "session_full.wav")
        print(f"[AI-WORKER] Loading audio from {audio_path}...")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Initialize transcriber
        engine = self.settings.transcription_engine
        print(f"[AI-WORKER] Initializing transcriber (engine: {engine})...")
        if engine == "gemini":
            transcriber = GeminiTranscriber(
                api_key=self.settings.gemini_api_key,
                model_name=self.settings.gemini_model_id
            )
        else:
            transcriber = LocalHFTranscriber(model_id=self.settings.local_model_id)

        # For simplicity, we transcribe the whole file at once
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        
        print(f"[AI-WORKER] Transcribing whole file ({len(audio_bytes)} bytes)...")
        result = await transcriber.transcribe(audio_bytes)
        print(f"[AI-WORKER] Transcription result received ({len(result.full_text)} chars)")
        
        # Save transcript
        transcript_path = os.path.join(abs_session_path, TRANSCRIPT_FILENAME)
        print(f"[AI-WORKER] Saving transcript to {transcript_path}...")
        data = {
            "full_text": result.full_text,
            "segments": [{"text": result.full_text, "timestamp": 0.0}]
        }
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def _run_summarization(self):
        abs_session_path = os.path.abspath(self.session.path)
        transcript_path = os.path.join(abs_session_path, TRANSCRIPT_FILENAME)
        print(f"[AI-WORKER] Loading transcript from {transcript_path}...")
        if not os.path.exists(transcript_path):
            raise FileNotFoundError("Transcript not found. Please transcribe first.")

        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle both list and dict formats for transcript.json
        if isinstance(data, list):
            transcript_text = " ".join([seg.get("text", "") for seg in data if isinstance(seg, dict)])
        elif isinstance(data, dict):
            transcript_text = data.get("full_text", "")
            if not transcript_text and "segments" in data:
                transcript_text = " ".join([seg.get("text", "") for seg in data["segments"] if isinstance(seg, dict)])
        else:
            transcript_text = ""
            
        print(f"[AI-WORKER] Summarizing text ({len(transcript_text)} chars)...")
        
        summarizer = GeminiSummarizer(
            api_key=self.settings.gemini_api_key,
            model_name=self.settings.gemini_model_id
        )
        
        summary = await summarizer.summarize(transcript_text)
        print(f"[AI-WORKER] Summary generated SUCCESS")
        
        summary_path = os.path.join(abs_session_path, SUMMARY_FILENAME)
        print(f"[AI-WORKER] Saving summary to {summary_path}...")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary.raw_markdown)
