from abc import ABC, abstractmethod
from typing import Callable
import numpy as np
from meeting_recorder.data.audio import AudioConfig

class CaptureEngine(ABC):
    def __init__(self, config: AudioConfig, callback: Callable[[np.ndarray], None]):
        self.config = config
        self.callback = callback
        self._is_active = False

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @property
    def is_active(self) -> bool:
        return self._is_active
