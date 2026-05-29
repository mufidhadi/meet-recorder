import pyaudiowpatch as pyaudio
import numpy as np
import wave

def diagnose_audio():
    p = pyaudio.PyAudio()
    try:
        # Get default WASAPI loopback
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        loopback_dev = None
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev["isLoopbackDevice"] and dev["name"].startswith(default_speakers["name"]):
                loopback_dev = dev
                break
        
        if not loopback_dev:
            print("No loopback device found")
            return

        print(f"Diagnosing Device: {loopback_dev['name']}")
        print(f"Native Sample Rate: {loopback_dev['defaultSampleRate']}")
        print(f"Max Input Channels: {loopback_dev['maxInputChannels']}")

        rate = int(loopback_dev['defaultSampleRate'])
        channels = loopback_dev['maxInputChannels']
        
        frames = []
        
        def callback(in_data, frame_count, time_info, status):
            frames.append(in_data)
            return (None, pyaudio.paContinue)

        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=loopback_dev['index'],
            stream_callback=callback
        )

        print("Recording 5 seconds of RAW audio... PLAY SOMETHING!")
        stream.start_stream()
        import time
        time.sleep(5)
        stream.stop_stream()
        stream.close()

        # Save to file with NATIVE format
        raw_data = b''.join(frames)
        with wave.open("diagnostic_raw.wav", "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(raw_data)
        
        print(f"Saved diagnostic_raw.wav ({channels} channels, {rate}Hz)")
        
    finally:
        p.terminate()

if __name__ == "__main__":
    diagnose_audio()
