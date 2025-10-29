"""Audio processing utilities for voice interactions.

This module provides functions for converting and processing audio data
for use with Twilio voice streams, including format conversion and
sound effect generation.
"""

import wave
import audioop
import base64
import soxr
import numpy as np

def openai_audio_to_twilio_mulaw(audio_data: np.ndarray) -> bytes:
    """
    Convert OpenAI PCM audio to Twilio μ-law format.
    This function converts PCM audio data to μ-law format and resamples it from 24kHz to 8kHz.
    The input audio data is expected to be in PCM format, and the output will be μ-law encoded bytes.
    Args:
        audio_data (np.ndarray): The PCM audio data.
    Returns:
        bytes: The μ-law encoded audio data.
    """
    # Normalize dtype
    if audio_data.dtype == np.int16:
        audio_data = audio_data.astype(np.float32) / 32768.0
    elif audio_data.dtype != np.float32:
        raise ValueError(f"Unsupported dtype: {audio_data.dtype}")

    # Resample from 24kHz → 8kHz
    resampled = soxr.resample(audio_data, 44100, 8000)

    # Convert to int16
    resampled_int16 = np.clip(
        resampled * 32768.0, -32768, 32767).astype(np.int16)

    # μ-law encode
    return audioop.lin2ulaw(resampled_int16.tobytes(), 2)

def get_computer_keyboard_typing_sound(seconds: int, sequence: int):
    """Generate keyboard typing sound effect in μ-law format.
    
    Reads a pre-recorded keyboard typing sound and converts it to μ-law
    format suitable for Twilio voice streams.
    
    Args:
        seconds: Duration in seconds (currently unused)
        sequence: Number of sequences (currently unused)
        
    Returns:
        str: Base64-encoded μ-law audio data
    """
    with wave.open('./routers/voice_utils/typing-with-delay.wav', "rb") as wav:  
        params = wav.getparams()
        # print(params)
    #     # print(params.framerate)
    #     # buffer_frames = params.framerate * seconds * sequence
    #     # frame_count = params.framerate * seconds
        raw_wav= wav.readframes(wav.getnframes())
        wav_data = np.frombuffer(raw_wav, dtype=np.int16)
        mulaw_data = openai_audio_to_twilio_mulaw(wav_data)
        return base64.b64encode(mulaw_data).decode("utf-8")
    #     # return base64.b64encode(raw_ulaw).decode("utf-8")
    #     # print(base64.b64encode(raw_ulaw).decode("utf-8"))
    #     return base64.b64encode(raw_ulaw).decode("utf-8")
    # return base64.b64encode(wav.readframes(wav.getnframes())).decode("utf-8")

if __name__ == "__main__":
    # get_computer_keyboard_typing_sound(1, 2)
    get_computer_keyboard_typing_sound(1, 2)