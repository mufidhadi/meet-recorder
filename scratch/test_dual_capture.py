import pyaudiowpatch as pyaudio
import numpy as np
import time
import wave

def test_dual_capture():
    p = pyaudio.PyAudio()
    try:
        # 1. Get Loopback
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        loopback_dev = None
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev["isLoopbackDevice"] and dev["name"].startswith(default_speakers["name"]):
                loopback_dev = dev
                break
        
        # 2. Get Mic
        mic_dev = p.get_device_info_by_index(wasapi_info["defaultInputDevice"])
        
        if not loopback_dev or not mic_dev:
            print(f"Devices missing: Loopback={bool(loopback_dev)}, Mic={bool(mic_dev)}")
            return

        print(f"Loopback: {loopback_dev['name']} at {loopback_dev['defaultSampleRate']}Hz")
        print(f"Mic: {mic_dev['name']} at {mic_dev['defaultSampleRate']}Hz")

        # Global buffers
        loopback_samples = []
        mic_samples = []
        mixed_samples = []

        def resample(audio, native_rate, target_rate=16000):
            if native_rate == target_rate:
                return audio
            skip = native_rate // target_rate
            return audio[::skip]

        def mono_mix(audio, channels):
            if channels == 1:
                return audio
            return audio.reshape(-1, channels).mean(axis=1).astype(np.int16)

        def loopback_callback(in_data, frame_count, time_info, status):
            raw = np.frombuffer(in_data, dtype=np.int16)
            mono = mono_mix(raw, loopback_dev['maxInputChannels'])
            resampled = resample(mono, int(loopback_dev['defaultSampleRate']))
            loopback_samples.extend(resampled.tolist())
            return (None, pyaudio.paContinue)

        def mic_callback(in_data, frame_count, time_info, status):
            raw = np.frombuffer(in_data, dtype=np.int16)
            mono = mono_mix(raw, mic_dev['maxInputChannels'])
            resampled = resample(mono, int(mic_dev['defaultSampleRate']))
            mic_samples.extend(resampled.tolist())
            return (None, pyaudio.paContinue)

        # Open streams
        s_loop = p.open(
            format=pyaudio.paInt16,
            channels=loopback_dev['maxInputChannels'],
            rate=int(loopback_dev['defaultSampleRate']),
            input=True,
            input_device_index=loopback_dev['index'],
            stream_callback=loopback_callback
        )

        s_mic = p.open(
            format=pyaudio.paInt16,
            channels=mic_dev['maxInputChannels'],
            rate=int(mic_dev['defaultSampleRate']),
            input=True,
            input_device_index=mic_dev['index'],
            stream_callback=mic_callback
        )

        print("Recording for 10 seconds... Speak and Play music!")
        s_loop.start_stream()
        s_mic.start_stream()

        start_time = time.time()
        while time.time() - start_time < 10:
            # Mix what we have
            n = min(len(loopback_samples), len(mic_samples))
            if n > 0:
                l_chunk = np.array(loopback_samples[:n], dtype=np.int32)
                m_chunk = np.array(mic_samples[:n], dtype=np.int32)
                
                # Simple sum with clipping
                mixed = np.clip(l_chunk + m_chunk, -32768, 32767).astype(np.int16)
                mixed_samples.extend(mixed.tolist())
                
                # Remove used samples
                del loopback_samples[:n]
                del mic_samples[:n]
            
            time.sleep(0.1)

        s_loop.stop_stream()
        s_mic.stop_stream()
        s_loop.close()
        s_mic.close()

        # Save Mixed
        mixed_data = np.array(mixed_samples, dtype=np.int16).tobytes()
        with wave.open("test_mixed.wav", "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(mixed_data)
        
        print(f"Saved test_mixed.wav. Duration: {len(mixed_samples)/16000:.2f}s")

    finally:
        p.terminate()

if __name__ == "__main__":
    test_dual_capture()
