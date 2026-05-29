# Design Doc: Dual Audio Capture (Mic + Loopback)

## 1. Problem Statement
The current implementation of `WindowsCaptureEngine` only captures audio from the WASAPI Loopback device (system output). This means the user's own voice (microphone input) is not recorded during meetings, leading to incomplete transcripts.

## 2. Objective
Modify `WindowsCaptureEngine` to simultaneously capture audio from the default communication input device (Microphone) and the default output device (Loopback), mix them in real-time, and provide a single mono 16kHz stream to the transcription pipeline.

## 3. Proposed Architecture
We will use a **Multi-Stream Software Mixer** approach:
- **Loopback Thread**: Captures system audio at its native rate/channels.
- **Mic Thread**: Captures microphone audio at its native rate/channels.
- **Mixing Logic**:
    - Convert both streams to Mono.
    - Resample both streams to 16,000 Hz.
    - Use thread-safe queues (buffers) to synchronize the two streams.
    - Sum the samples and apply a 0.5x gain (optional/configurable) to prevent clipping.
    - Clip values to the int16 range [-32768, 32767].

## 4. Components & Data Flow

### 4.1. WindowsCaptureEngine Refactoring
- `_loopback_stream`: Dedicated stream for system audio.
- `_mic_stream`: Dedicated stream for microphone audio.
- `_loopback_buffer` & `_mic_buffer`: `collections.deque` or `queue.Queue` to hold resampled mono samples.
- `_mixer_thread`: A background thread that pulls samples from both buffers, mixes them, and calls the user-provided callback.

### 4.2. Processing Steps (per callback)
1. **Raw Capture**: Get data from PyAudio callback.
2. **Mixdown to Mono**: Average channels if stereo.
3. **Resample**: Downsample to 16kHz using simple decimation.
4. **Queueing**: Push processed samples to respective buffer.

### 4.3. Mixing Loop
```python
while not stopped:
    # Wait until both buffers have enough samples for a small window (e.g. 100ms)
    # Pull n samples from loopback
    # Pull n samples from mic
    # mixed = clip(loopback + mic)
    # callback(mixed)
```

## 5. Error Handling
- **Mic Not Found**: If the microphone cannot be opened, the engine should fallback to Loopback-only mode with a warning log.
- **Sample Rate Mismatch**: Handle cases where loopback and mic have different native sample rates (handled by per-stream resampling).

## 6. Testing Strategy
1. **Unit Test (Mocked Audio)**: Feed known sine waves into the internal processing methods and verify the mixed output is a sum of both.
2. **Integration Test**: Use `scratch/test_dual_capture.py` (already created) to verify real hardware interaction.

## 7. Success Criteria
- Final saved `.wav` chunks in `recordings/` contain both system audio (e.g., music/other speakers) and the user's voice (microphone).
- Transcription shows dialogue from both the user and other participants.
- No impact on other applications' ability to use the mic.
