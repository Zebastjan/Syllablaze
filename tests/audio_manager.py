#!/usr/bin/env python3
"""
Test script for the unified AudioProcessor class.

This script tests the core functionality of the AudioProcessor class
to ensure it correctly handles audio data manipulation for Syllablaze.
"""

import os
import sys
import numpy as np
import tempfile
import pytest
import logging
from scipy import signal

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path to import our module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the AudioProcessor class
try:
    from blaze.audio_processor import AudioProcessor
    logger.info("Successfully imported AudioProcessor")
except ImportError:
    logger.error("Failed to import AudioProcessor. Make sure it's in the correct path.")
    sys.exit(1)

def test_frames_to_numpy():
    """Test conversion of audio frames to NumPy array"""
    # Create some dummy audio frames
    dummy_frames = [
        np.array([0, 100, 200, 300], dtype=np.int16).tobytes(),
        np.array([400, 500, 600, 700], dtype=np.int16).tobytes()
    ]

    # Convert frames to numpy array
    result = AudioProcessor.frames_to_numpy(dummy_frames)

    # Check result
    assert isinstance(result, np.ndarray), "Result should be a NumPy array"
    assert result.dtype == np.int16, "Result should have dtype int16"
    assert len(result) == 8, "Result should have 8 elements"
    assert result[0] == 0 and result[4] == 400, "Result should contain correct values"

    logger.info("frames_to_numpy test passed")

def test_calculate_volume():
    """Test volume level calculation"""
    # Test with silence (zeros)
    silence = np.zeros(1000, dtype=np.int16)
    silence_volume = AudioProcessor.calculate_volume(silence)
    assert silence_volume == 0.0, "Silence should have volume 0.0"

    # Test with maximum volume
    max_volume = np.ones(1000, dtype=np.int16) * 32767  # Max value for int16
    max_volume_level = AudioProcessor.calculate_volume(max_volume)
    assert max_volume_level > 0.9, "Maximum volume should be close to 1.0"

    # Test with medium volume
    medium_volume = np.ones(1000, dtype=np.int16) * 16384  # Half of max value
    medium_volume_level = AudioProcessor.calculate_volume(medium_volume)
    assert 0.4 < medium_volume_level < 0.6, "Medium volume should be around 0.5"

    logger.info("calculate_volume test passed")

def test_resample_audio():
    """Test audio resampling"""
    # Create a test signal
    original_rate = 44100
    duration = 1  # 1 second
    t = np.linspace(0, duration, int(original_rate * duration), endpoint=False)
    # 440 Hz sine wave
    test_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    # Resample to Whisper's 16kHz
    target_rate = 16000
    resampled = AudioProcessor.resample_audio(test_signal, original_rate, target_rate)

    # Check result
    assert isinstance(resampled, np.ndarray), "Result should be a NumPy array"
    assert len(resampled) == int(duration * target_rate), f"Result should have {int(duration * target_rate)} samples"

    # Test that resampling is a no-op when rates match
    same_rate = AudioProcessor.resample_audio(test_signal, original_rate, original_rate)
    assert len(same_rate) == len(test_signal), "Resampling with same rate should return original length"

    logger.info("resample_audio test passed")

def test_convert_to_whisper_format():
    """Test conversion to Whisper format"""
    # Create a test signal
    original_rate = 44100
    duration = 1  # 1 second
    t = np.linspace(0, duration, int(original_rate * duration), endpoint=False)
    # 440 Hz sine wave
    test_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    # Convert to Whisper format
    whisper_format = AudioProcessor.convert_to_whisper_format(test_signal, original_rate)

    # Check result
    assert isinstance(whisper_format, np.ndarray), "Result should be a NumPy array"
    assert whisper_format.dtype == np.float32, "Result should have dtype float32"
    assert len(whisper_format) == int(duration * AudioProcessor.WHISPER_SAMPLE_RATE), f"Result should have {int(duration * AudioProcessor.WHISPER_SAMPLE_RATE)} samples"
    assert -1.0 <= whisper_format.max() <= 1.0, "Values should be normalized to [-1.0, 1.0]"
    assert -1.0 <= whisper_format.min() <= 1.0, "Values should be normalized to [-1.0, 1.0]"

    logger.info("convert_to_whisper_format test passed")

def test_process_audio_for_transcription():
    """Test the high-level audio processing function"""
    # Create some dummy audio frames
    original_rate = 44100
    duration = 1  # 1 second
    t = np.linspace(0, duration, int(original_rate * duration), endpoint=False)
    # 440 Hz sine wave
    test_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    test_frames = [test_signal.tobytes()]

    # Process audio for transcription
    processed = AudioProcessor.process_audio_for_transcription(test_frames, original_rate)

    # Check result
    assert isinstance(processed, np.ndarray), "Result should be a NumPy array"
    assert processed.dtype == np.float32, "Result should have dtype float32"
    assert len(processed) == int(duration * AudioProcessor.WHISPER_SAMPLE_RATE), f"Result should have {int(duration * AudioProcessor.WHISPER_SAMPLE_RATE)} samples"
    assert -1.0 <= processed.max() <= 1.0, "Values should be normalized to [-1.0, 1.0]"

    logger.info("process_audio_for_transcription test passed")

def test_save_to_wav():
    """Test saving audio data to WAV file"""
    # Create a test signal
    sample_rate = 16000
    duration = 1  # 1 second
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # 440 Hz sine wave
    test_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    # Create a temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)

    try:
        # Save to WAV file
        result = AudioProcessor.save_to_wav(test_signal, temp_path, sample_rate)
        assert result, "save_to_wav should return True on success"

        # Check that file exists and has non-zero size
        assert os.path.exists(temp_path), "WAV file should exist"
        assert os.path.getsize(temp_path) > 0, "WAV file should have non-zero size"

        # Additional checks could be done by reading the file back and comparing

        logger.info("save_to_wav test passed")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    # Run all tests
    try:
        test_frames_to_numpy()
        test_calculate_volume()
        test_resample_audio()
        test_convert_to_whisper_format()
        test_process_audio_for_transcription()
        test_save_to_wav()

        print("All tests passed successfully!")
        sys.exit(0)
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

