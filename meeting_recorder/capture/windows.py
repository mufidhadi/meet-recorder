import pyaudiowpatch as pyaudio
import numpy as np
import threading
import collections
import time
from typing import Callable
from meeting_recorder.capture.engine import CaptureEngine
from meeting_recorder.data.audio import AudioConfig
from meeting_recorder.processing.audio import mix_audio

class WindowsCaptureEngine(CaptureEngine):
    def __init__(self, config: AudioConfig, callback: Callable[[np.ndarray], None], vu_callback: Callable[[float, float], None] = None):
        super().__init__(config, callback)
        self.vu_callback = vu_callback
        self._pa = pyaudio.PyAudio()
        self._loopback_stream = None
        self._mic_stream = None
        self._stop_event = threading.Event()
        
        # Deques of numpy arrays for efficient buffering
        self._loopback_buffer = collections.deque() 
        self._mic_buffer = collections.deque()
        self._mixer_thread = None
        self._lock = threading.Lock()
        
        # Stream parameters
        self._loopback_channels = 0
        self._loopback_rate = 0
        self._mic_channels = 0
        self._mic_rate = 0

    def _get_default_loopback_device(self):
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self._pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            for i in range(self._pa.get_device_count()):
                dev = self._pa.get_device_info_by_index(i)
                if dev["isLoopbackDevice"] and dev["name"].startswith(default_speakers["name"]):
                    return dev
            return None
        except Exception:
            return None

    def _get_default_mic_device(self):
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            return self._pa.get_device_info_by_index(wasapi_info["defaultInputDevice"])
        except Exception:
            return None

    def _process_stream_data(self, in_data, n_channels, native_rate):
        raw_audio = np.frombuffer(in_data, dtype=np.int16)
        if n_channels > 1:
            raw_audio = raw_audio.reshape(-1, n_channels).mean(axis=1).astype(np.int16)
        
        target_rate = self.config.sample_rate
        if native_rate != target_rate:
            skip = native_rate // target_rate
            return raw_audio[::skip].copy()
        return raw_audio.copy()

    def _calculate_level(self, data: np.ndarray) -> float:
        if len(data) == 0:
            return 0.0
        # RMS level normalized to 0.0 - 1.0
        float_data = data.astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(float_data**2))
        return min(float(rms) * 5.0, 1.0) # Scale up for better visualization

    def _loopback_callback(self, in_data, frame_count, time_info, status):
        if self._stop_event.is_set():
            return (None, pyaudio.paAbort)
        
        processed = self._process_stream_data(in_data, self._loopback_channels, self._loopback_rate)
        with self._lock:
            self._loopback_buffer.append(processed)
            
        return (in_data, pyaudio.paContinue)

    def _mic_callback(self, in_data, frame_count, time_info, status):
        if self._stop_event.is_set():
            return (None, pyaudio.paAbort)
            
        processed = self._process_stream_data(in_data, self._mic_channels, self._mic_rate)
        with self._lock:
            self._mic_buffer.append(processed)
            
        return (in_data, pyaudio.paContinue)

    def _mixer_loop(self):
        """Background thread that mixes loopback and mic audio. 
        Fluid mixing: outputs available data even if one stream is lagging.
        """
        loopback_residue = np.array([], dtype=np.int16)
        mic_residue = np.array([], dtype=np.int16)
        
        while not self._stop_event.is_set():
            new_loopback = []
            new_mic = []
            
            with self._lock:
                while self._loopback_buffer:
                    new_loopback.append(self._loopback_buffer.popleft())
                while self._mic_buffer:
                    new_mic.append(self._mic_buffer.popleft())
            
            if new_loopback:
                lb_data = np.concatenate(new_loopback)
                loopback_residue = np.concatenate([loopback_residue, lb_data])
                if self.vu_callback:
                    self.vu_callback(self._calculate_level(lb_data), -1.0)
            if new_mic:
                m_data = np.concatenate(new_mic)
                mic_residue = np.concatenate([mic_residue, m_data])
                if self.vu_callback:
                    self.vu_callback(-1.0, self._calculate_level(m_data))
            
            # Fluid Mixing:
            # We want to keep audio flowing. We mix based on the LONGEST buffer 
            # if the shorter one hasn't sent data in a while, or just mix the MIN.
            # To keep it simple but non-blocking:
            # If both have data, mix the intersection.
            # If one has data and the other has been empty for > 100ms, 
            # mix the available data with silence.
            
            n_lb = len(loopback_residue)
            n_mic = len(mic_residue)
            
            n = min(n_lb, n_mic)
            
            if n > 0:
                # Normal mixing
                mixed = mix_audio(loopback_residue[:n], mic_residue[:n])
                self.callback(mixed)
                loopback_residue = loopback_residue[n:]
                mic_residue = mic_residue[n:]
            elif n_lb > 1600: # > 100ms of lag
                # Mic is lagging/dead, output loopback only
                self.callback(loopback_residue[:1600])
                loopback_residue = loopback_residue[1600:]
            elif n_mic > 1600: # > 100ms of lag
                # Loopback is lagging/dead, output mic only
                self.callback(mic_residue[:1600])
                mic_residue = mic_residue[1600:]
            
            time.sleep(0.01)

    def start(self):
        if self._is_active:
            return

        print("[ENGINE] Starting WindowsCaptureEngine...")
        loopback_dev = self._get_default_loopback_device()
        mic_dev = self._get_default_mic_device()
        
        if not loopback_dev:
            print("[ENGINE] ERROR: Could not find WASAPI loopback device.")
            raise RuntimeError("Could not find WASAPI loopback device.")
        if not mic_dev:
            print("[ENGINE] ERROR: Could not find default microphone device.")
            raise RuntimeError("Could not find default microphone device.")

        print(f"[ENGINE] Loopback device: {loopback_dev['name']}")
        print(f"[ENGINE] Mic device: {mic_dev['name']}")

        self._stop_event.clear()
        
        # Loopback parameters
        self._loopback_rate = int(loopback_dev["defaultSampleRate"])
        self._loopback_channels = int(loopback_dev["maxInputChannels"])

        # Mic parameters
        self._mic_rate = int(mic_dev["defaultSampleRate"])
        self._mic_channels = int(mic_dev["maxInputChannels"])

        # Clear buffers
        with self._lock:
            self._loopback_buffer.clear()
            self._mic_buffer.clear()

        # Open Streams
        print("[ENGINE] Opening streams...")
        self._loopback_stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self._loopback_channels,
            rate=self._loopback_rate,
            input=True,
            input_device_index=loopback_dev["index"],
            stream_callback=self._loopback_callback
        )
        
        self._mic_stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self._mic_channels,
            rate=self._mic_rate,
            input=True,
            input_device_index=mic_dev["index"],
            stream_callback=self._mic_callback
        )
        
        # Start Mixer
        print("[ENGINE] Starting mixer thread...")
        self._mixer_thread = threading.Thread(target=self._mixer_loop, daemon=True)
        self._mixer_thread.start()
        
        self._is_active = True
        self._loopback_stream.start_stream()
        self._mic_stream.start_stream()
        print("[ENGINE] Engine active and streaming.")

    def stop(self):
        if not self._is_active:
            return
        
        self._stop_event.set()
        
        if self._loopback_stream:
            self._loopback_stream.stop_stream()
            self._loopback_stream.close()
            self._loopback_stream = None
            
        if self._mic_stream:
            self._mic_stream.stop_stream()
            self._mic_stream.close()
            self._mic_stream = None
            
        if self._mixer_thread:
            self._mixer_thread.join(timeout=1.0)
            self._mixer_thread = None
        
        self._is_active = False

    def __del__(self):
        try:
            self.stop()
            self._pa.terminate()
        except Exception:
            pass
