import numpy as np
import threading

class RingBuffer:
    def __init__(self, maxsize_seconds: float, sample_rate: int):
        self.sample_rate = sample_rate
        self.max_samples = int(maxsize_seconds * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.int16)
        self.write_index = 0
        self.size = 0
        self.lock = threading.Lock()

    def push(self, data: np.ndarray):
        with self.lock:
            n = len(data)
            if n > self.max_samples:
                data = data[-self.max_samples:]
                n = self.max_samples
            
            end_space = self.max_samples - self.write_index
            if n <= end_space:
                self.buffer[self.write_index:self.write_index + n] = data
            else:
                self.buffer[self.write_index:] = data[:end_space]
                self.buffer[:n - end_space] = data[end_space:]
            
            self.write_index = (self.write_index + n) % self.max_samples
            self.size = min(self.size + n, self.max_samples)

    def get_last_n_seconds(self, n_seconds: float) -> np.ndarray:
        with self.lock:
            n_samples = int(n_seconds * self.sample_rate)
            n_samples = min(n_samples, self.size)
            
            if n_samples == 0:
                return np.array([], dtype=np.int16)
            
            start = (self.write_index - n_samples) % self.max_samples
            if start + n_samples <= self.max_samples:
                return self.buffer[start:start + n_samples].copy()
            else:
                part1 = self.buffer[start:]
                part2 = self.buffer[:n_samples - len(part1)]
                return np.concatenate([part1, part2])

    @property
    def available_seconds(self) -> float:
        with self.lock:
            return self.size / self.sample_rate
