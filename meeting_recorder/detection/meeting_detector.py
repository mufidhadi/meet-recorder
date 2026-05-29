import threading
import time
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from .process_detector import ProcessDetector
from .window_detector import WindowDetector
from .network_detector import NetworkDetector
from .audio_analyzer import AudioAnalyzer

class MeetingState(Enum):
    NO_MEETING   = "no_meeting"
    LIKELY       = "likely_meeting"    # 30-49 points
    IN_MEETING   = "in_meeting"        # ≥ 50 points
    UNCERTAIN    = "uncertain"         # After IN_MEETING, drops to 20-49

@dataclass
class DetectionResult:
    state: MeetingState
    total_score: int
    breakdown: dict[str, int]
    app_detected: str = ""
    confidence: float = 0.0

START_THRESHOLD = 50    
STOP_THRESHOLD  = 20    
STOP_GRACE_S    = 60    

class MeetingDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        poll_interval_s: float = 5.0,
        on_meeting_start: Optional[Callable] = None,
        on_meeting_end: Optional[Callable] = None,
    ):
        self.sr = sample_rate
        self.poll_interval = poll_interval_s
        self.on_meeting_start = on_meeting_start
        self.on_meeting_end = on_meeting_end
        
        self._process_det = ProcessDetector()
        self._window_det = WindowDetector()
        self._network_det = NetworkDetector()
        self._audio_analyzer = AudioAnalyzer(sample_rate)
        
        self._state = MeetingState.NO_MEETING
        self._below_threshold_since: Optional[float] = None
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def push_audio(self, chunk: np.ndarray) -> None:
        """Call this from AudioCaptureEngine callback."""
        self._audio_analyzer.push_audio(chunk)

    def detect_once(self) -> DetectionResult:
        """Runs one detection cycle and returns result."""
        breakdown = {}
        total_score = 0
        detected_app = ""

        # --- Signal 1: Process ---
        proc_matches = self._process_det.detect()
        if proc_matches:
            best = max(proc_matches, key=lambda m: m.score)
            breakdown["process"] = best.score
            total_score += best.score
            detected_app = best.app_name

        # --- Signal 2: Window Title ---
        win_matches = self._window_det.detect()
        if win_matches:
            best = max(win_matches, key=lambda m: m.score)
            breakdown["window"] = best.score
            total_score += best.score
            if not detected_app:
                detected_app = best.app_name

        # --- Signal 3: Network ---
        net_matches = self._network_det.detect()
        if net_matches:
            best = max(net_matches, key=lambda m: m.score)
            breakdown["network"] = best.score
            total_score += best.score

        # --- Signal 4: Audio Analysis ---
        audio_analysis = self._audio_analyzer.analyze()
        if audio_analysis:
            breakdown["audio"] = audio_analysis.score
            total_score += audio_analysis.score

        # --- State Machine ---
        with self._lock:
            if total_score >= START_THRESHOLD:
                new_state = MeetingState.IN_MEETING
                self._below_threshold_since = None
            elif total_score >= 30:
                new_state = MeetingState.LIKELY
                self._below_threshold_since = None
            elif self._state == MeetingState.IN_MEETING and total_score >= STOP_THRESHOLD:
                new_state = MeetingState.UNCERTAIN
                self._below_threshold_since = self._below_threshold_since or time.time()
            else:
                # Check grace period before stop
                if (self._below_threshold_since and 
                    time.time() - self._below_threshold_since > STOP_GRACE_S):
                    new_state = MeetingState.NO_MEETING
                    self._below_threshold_since = None
                else:
                    new_state = self._state  

            # Trigger callbacks
            if new_state == MeetingState.IN_MEETING and self._state != MeetingState.IN_MEETING:
                if self.on_meeting_start:
                    self.on_meeting_start()
            
            if new_state == MeetingState.NO_MEETING and self._state != MeetingState.NO_MEETING:
                if self.on_meeting_end:
                    self.on_meeting_end()

            self._state = new_state
            
        confidence = min(total_score / 100.0, 1.0)
        
        return DetectionResult(
            state=new_state,
            total_score=total_score,
            breakdown=breakdown,
            app_detected=detected_app,
            confidence=confidence,
        )

    def _poll_loop(self):
        while self._running:
            try:
                self.detect_once()
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def start_monitoring(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
