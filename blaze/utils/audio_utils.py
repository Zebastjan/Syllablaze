"""
Audio Processing Utilities for Syllablaze

This module provides abstractions for audio processing operations, including:
- Converting audio frames to numpy arrays
- Resampling audio to the format expected by Whisper
- Saving audio to WAV files
- Getting device sample rates
"""

import numpy as np
import wave
from scipy import signal
import logging

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handles audio processing operations with appropriate abstraction"""
    
    @staticmethod
    def get_device_sample_rate(audio_instance, device_info=None):
        """Get the sample rate for a device"""
        if device_info is not None:
            return int(device_info['defaultSampleRate'])
        else:
            # If no device info is available, use default input device
            return int(audio_instance.get_default_input_device_info()['defaultSampleRate'])
    
    @staticmethod
    def convert_to_whisper_format(audio_data, original_rate, target_rate):
        """Convert audio data to the format expected by Whisper"""
        # Resample if needed
        if original_rate != target_rate:
            logger.info(f"Resampling audio from {original_rate}Hz to {target_rate}Hz")
            ratio = target_rate / original_rate
            output_length = int(len(audio_data) * ratio)
            audio_data = signal.resample(audio_data, output_length)
        else:
            logger.info(f"No resampling needed, audio already at {target_rate}Hz")
        
        # Normalize to float32 in range [-1.0, 1.0]
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        return audio_data
    
    @staticmethod
    def save_to_wav(audio_data, filename, sample_rate, channels=1, sample_width=2):
        """Save audio data to a WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
        wf.close()
        
    @staticmethod
    def frames_to_numpy(frames, dtype=np.int16):
        """Convert audio frames to numpy array"""
        return np.frombuffer(b''.join(frames), dtype=dtype)
    
    @staticmethod
    def calculate_volume(audio_data):
        """Calculate volume level from audio data"""
        if len(audio_data) > 0:
            # Calculate RMS with protection against zero/negative values
            squared = np.abs(audio_data)**2
            mean_squared = np.mean(squared) if np.any(squared) else 0
            rms = np.sqrt(mean_squared) if mean_squared > 0 else 0
            # Normalize to 0-1 range
            volume = min(1.0, max(0.0, rms / 32768.0))
        else:
            volume = 0.0
        return volume