"""
Unified Audio Processing for Syllablaze - OPTIMIZED VERSION

This module provides a comprehensive audio processing system that consolidates
functionality previously scattered between recorder.py and audio_utils.py.

Key features:
- Audio frame conversion and manipulation with improved performance
- Volume level calculation
- Optimized resampling for Whisper compatibility
- Unified interface for audio file operations
- Memory-efficient processing
"""

import numpy as np
from scipy import signal
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Unified audio processing class for Syllablaze.

    This class handles all audio data manipulation needs including:
    - Converting audio frames to numpy arrays
    - Calculating volume levels
    - Resampling audio to Whisper format
    - Saving audio to files when needed
    """

    # Constants for Whisper compatibility
    WHISPER_SAMPLE_RATE = 16000  # 16kHz for Whisper

    @staticmethod
    def frames_to_numpy(frames: List[bytes], dtype=np.int16) -> np.ndarray:
        """
        Convert a list of audio frames to a numpy array.

        Args:
            frames: List of audio frame bytes
            dtype: NumPy data type (default: np.int16)

        Returns:
            NumPy array containing the audio data
        """
        if not frames:
            logger.warning("Empty frames list provided to frames_to_numpy")
            return np.array([], dtype=dtype)

        try:
            # Optimized implementation: convert each frame to array first, then concatenate
            # This avoids the intermediate byte join operation which can be expensive
            frame_arrays = [np.frombuffer(frame, dtype=dtype) for frame in frames]
            return np.concatenate(frame_arrays) if frame_arrays else np.array([], dtype=dtype)
        except Exception as e:
            logger.error(f"Error converting frames to numpy array: {e}")
            # Fall back to original method if the optimized approach fails
            try:
                return np.frombuffer(b''.join(frames), dtype=dtype)
            except Exception:
                return np.array([], dtype=dtype)

    @staticmethod
    def calculate_volume(audio_data: np.ndarray) -> float:
        """
        Calculate normalized volume level from audio data.

        Args:
            audio_data: NumPy array of audio samples

        Returns:
            Normalized volume level (0.0 to 1.0)
        """
        if len(audio_data) == 0:
            return 0.0

        try:
            # Calculate RMS with protection against zero/negative values
            squared = np.abs(audio_data)**2
            mean_squared = np.mean(squared) if np.any(squared) else 0
            rms = np.sqrt(mean_squared) if mean_squared > 0 else 0

            # Normalize to 0-1 range (assuming 16-bit audio)
            max_value = 32768.0  # For 16-bit audio
            volume = min(1.0, max(0.0, rms / max_value))

            return volume
        except Exception as e:
            logger.error(f"Error calculating volume: {e}")
            return 0.0

    @staticmethod
    def get_device_sample_rate(audio_instance, device_info: Optional[Dict[str, Any]] = None) -> int:
        """
        Get the sample rate for a device.

        Args:
            audio_instance: PyAudio instance
            device_info: Device info dictionary (optional)

        Returns:
            Sample rate in Hz
        """
        try:
            if device_info is not None:
                return int(device_info['defaultSampleRate'])
            else:
                # If no device info is available, use default input device
                return int(audio_instance.get_default_input_device_info()['defaultSampleRate'])
        except Exception as e:
            logger.error(f"Error getting device sample rate: {e}")
            return 44100  # Fallback to a standard rate

    @staticmethod
    def resample_audio(audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """
        Resample audio data to a new sample rate with optimized performance.

        Args:
            audio_data: NumPy array of audio samples
            original_rate: Original sample rate in Hz
            target_rate: Target sample rate in Hz

        Returns:
            Resampled audio data as NumPy array
        """
        if original_rate == target_rate:
            logger.info(f"No resampling needed, audio already at {target_rate}Hz")
            return audio_data

        try:
            # Try to use librosa's resampling which can be faster
            try:
                import librosa
                logger.info(f"Resampling audio from {original_rate}Hz to {target_rate}Hz using librosa")
                # Convert to float32 first for librosa (normalized to [-1, 1])
                float_data = audio_data.astype(np.float32) / 32768.0
                resampled_data = librosa.resample(
                    float_data, 
                    orig_sr=original_rate,
                    target_sr=target_rate
                )
                # Convert back to int16 range if needed
                return (resampled_data * 32768.0).astype(np.int16)
            except ImportError:
                # Fall back to scipy's resampling if librosa is not available
                logger.info(f"Librosa not available, using scipy for resampling from {original_rate}Hz to {target_rate}Hz")
                ratio = target_rate / original_rate
                output_length = int(len(audio_data) * ratio)
                resampled_data = signal.resample(audio_data, output_length)
                return resampled_data
        except Exception as e:
            logger.error(f"Error resampling audio: {e}")
            # Fall back to standard resampling
            logger.info(f"Falling back to standard resampling from {original_rate}Hz to {target_rate}Hz")
            ratio = target_rate / original_rate
            output_length = int(len(audio_data) * ratio)
            resampled_data = signal.resample(audio_data, output_length)
            return resampled_data

    @staticmethod
    def convert_to_whisper_format(audio_data: np.ndarray, original_rate: int) -> np.ndarray:
        """
        Convert audio data to the format expected by Whisper with optimized processing.
        
        This method automatically handles resampling and normalization in an optimized way.

        Args:
            audio_data: NumPy array of audio samples
            original_rate: Original sample rate in Hz

        Returns:
            Audio data in Whisper-compatible format (float32, [-1.0, 1.0], 16kHz)
        """
        try:
            if original_rate != AudioProcessor.WHISPER_SAMPLE_RATE:
                # First try librosa which returns already normalized data
                try:
                    import librosa
                    # Resample and normalize in one step with librosa
                    float_data = audio_data.astype(np.float32) / 32768.0
                    whisper_data = librosa.resample(
                        float_data,
                        orig_sr=original_rate,
                        target_sr=AudioProcessor.WHISPER_SAMPLE_RATE
                    )
                    return whisper_data
                except ImportError:
                    # Fall back to scipy's resampling + separate normalization
                    resampled_data = AudioProcessor.resample_audio(
                        audio_data, original_rate, AudioProcessor.WHISPER_SAMPLE_RATE
                    )
                    # Normalize to float32 in range [-1.0, 1.0]
                    return resampled_data.astype(np.float32) / 32768.0
            else:
                # Just normalize without resampling
                return audio_data.astype(np.float32) / 32768.0
        except Exception as e:
            logger.error(f"Error converting to Whisper format: {e}")
            # Try to recover with basic conversion if possible
            return np.array(audio_data, dtype=np.float32) / 32768.0

    @staticmethod
    def process_audio_for_transcription(
        frames: List[bytes],
        original_rate: int
    ) -> np.ndarray:
        """
        Process recorded audio frames for transcription with Whisper.
        
        This is a high-level function that combines multiple processing steps
        with optimized performance.

        Args:
            frames: List of audio frame bytes
            original_rate: Original sample rate in Hz

        Returns:
            Processed audio data ready for Whisper transcription
        """
        try:
            # Convert frames to numpy array using optimized method
            audio_data = AudioProcessor.frames_to_numpy(frames)

            # Convert to Whisper format (resample and normalize) with optimized processing
            processed_data = AudioProcessor.convert_to_whisper_format(
                audio_data, original_rate
            )

            logger.info(f"Audio processed for transcription: {len(processed_data)} samples at {AudioProcessor.WHISPER_SAMPLE_RATE}Hz")
            return processed_data
        except Exception as e:
            logger.error(f"Error processing audio for transcription: {e}")
            raise

    @staticmethod
    def save_to_wav(
        audio_data: np.ndarray,
        filename: str,
        sample_rate: int,
        channels: int = 1,
        sample_width: int = 2
    ) -> bool:
        """
        Save audio data to a WAV file.

        Args:
            audio_data: NumPy array of audio samples
            filename: Output filename
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            sample_width: Sample width in bytes

        Returns:
            True if successful, False otherwise
        """
        try:
            import wave
            wf = wave.open(filename, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
            wf.close()
            logger.info(f"Audio saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving audio to WAV file: {e}")
            return False