from dataclasses import dataclass

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16
    capture_microphone: bool = True
    capture_system_audio: bool = True
