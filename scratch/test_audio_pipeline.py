import time
import os
from meeting_recorder.data.audio import AudioConfig
from meeting_recorder.capture.windows import WindowsCaptureEngine
from meeting_recorder.processing.buffer import RingBuffer
from meeting_recorder.processing.chunker import AudioChunker

def main():
    config = AudioConfig(sample_rate=16000)
    # Buffering up to 60 seconds
    buffer = RingBuffer(maxsize_seconds=60, sample_rate=16000)
    
    chunk_count = 0
    
    def on_chunk(wav_bytes):
        nonlocal chunk_count
        filename = f"chunk_{chunk_count}.wav"
        with open(filename, "wb") as f:
            f.write(wav_bytes)
        print(f"Saved {filename} ({len(wav_bytes)} bytes)")
        chunk_count += 1

    # Initialize components
    engine = WindowsCaptureEngine(config, callback=buffer.push)
    chunker = AudioChunker(buffer, chunk_duration_s=5.0, on_chunk_callback=on_chunk)

    print("Starting audio pipeline (5s chunks)...")
    print("Recording for 12 seconds to get 2 chunks. PLEASE PLAY SOME AUDIO!")
    
    engine.start()
    chunker.start()

    try:
        time.sleep(12)
    finally:
        print("Stopping...")
        engine.stop()
        chunker.stop()
        print(f"Integration test complete. Total chunks: {chunk_count}")

if __name__ == "__main__":
    main()
