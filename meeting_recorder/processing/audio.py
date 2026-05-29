import numpy as np

def mix_audio(loopback: np.ndarray, mic: np.ndarray) -> np.ndarray:
    """
    Mixes two audio arrays by summing them and clipping to int16 range.
    
    Args:
        loopback: NumPy array of int16 audio samples from system loopback.
        mic: NumPy array of int16 audio samples from microphone.
        
    Returns:
        Mixed audio as a NumPy array of int16.
    """
    # Ensure they are the same length for this utility
    n = min(len(loopback), len(mic))
    l = loopback[:n].astype(np.int32)
    m = mic[:n].astype(np.int32)
    mixed = np.clip(l + m, -32768, 32767)
    return mixed.astype(np.int16)
