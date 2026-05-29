import numpy as np
from scipy import signal as scipy_signal
from dataclasses import dataclass

@dataclass
class AudioAnalysis:
    speech_energy_ratio: float
    silence_ratio: float
    spectral_flatness: float
    zero_crossing_rate: float
    has_rhythm: bool
    score: int

class AudioAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self.sr = sample_rate
        self._buffer: list[np.ndarray] = []
        self._max_buffer_s = 10 
    
    def push_audio(self, chunk: np.ndarray) -> None:
        self._buffer.append(chunk.astype(np.float32) / 32768.0)
        total_samples = sum(len(c) for c in self._buffer)
        max_samples = self._max_buffer_s * self.sr
        while total_samples > max_samples and self._buffer:
            removed = self._buffer.pop(0)
            total_samples -= len(removed)

    def analyze(self) -> AudioAnalysis | None:
        if not self._buffer:
            return None
        
        audio = np.concatenate(self._buffer)
        if len(audio) < self.sr: # Need at least 1s
            return None
            
        freqs, psd = scipy_signal.welch(audio, self.sr, nperseg=512)
        speech_mask = (freqs >= 300) & (freqs <= 3500)
        speech_energy = np.sum(psd[speech_mask])
        total_energy = np.sum(psd) + 1e-10
        speech_ratio = float(speech_energy / total_energy)
        
        frame_size = int(0.02 * self.sr)
        frames = [audio[i:i+frame_size] for i in range(0, len(audio)-frame_size, frame_size)]
        rms_values = [np.sqrt(np.mean(f**2)) for f in frames]
        silence_ratio = sum(1 for r in rms_values if r < 0.01) / (len(rms_values) + 1e-10)
        
        geometric_mean = np.exp(np.mean(np.log(psd + 1e-10)))
        arithmetic_mean = np.mean(psd) + 1e-10
        spectral_flatness = float(geometric_mean / arithmetic_mean)
        
        signs = np.sign(audio)
        zcr = float(np.mean(np.abs(np.diff(signs)) / 2))
        
        score = 0
        if speech_ratio > 0.55:          score += 4
        if silence_ratio > 0.15:         score += 3
        if spectral_flatness > 0.1:      score += 2
        if 0.03 < zcr < 0.25:           score += 2
        
        return AudioAnalysis(
            speech_energy_ratio=speech_ratio,
            silence_ratio=silence_ratio,
            spectral_flatness=spectral_flatness,
            zero_crossing_rate=zcr,
            has_rhythm=False, # Simplification
            score=min(score, 15),
        )
