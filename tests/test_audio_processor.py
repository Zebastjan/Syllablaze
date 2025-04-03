"""
tests/test_audio_processor.py - Tests for the unified AudioProcessor class

This file contains pytest-compatible tests for the AudioProcessor class
in the Syllablaze application.
"""

import os
import sys
import numpy as np
import tempfile
import pytest
from scipy import signal

# Add parent directory to path to import our module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the AudioProcessor class
from blaze.audio_processor import AudioProcessor

@pytest.fixture
def sample_audio_frames():
    """Fixture providing sample audio frames for testing"""
    return [
        np.array([0, 100, 200, 300], dtype=np.int16).tobytes(),
        np.array([400, 500, 600, 700], dtype=np.int16).tobytes()
    ]

@pytest.fixture
def sine_wave_audio():
    """Fixture providing a sine wave audio sample"""
    sample_rate = 44100
    duration = 1  # 1 second
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # 440 Hz sine wave
    test_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    return test_signal, sample_rate

def test_frames_to_numpy(sample_audio_frames):
    """Test conversion of audio frames to NumPy array"""
    # Convert frames to numpy array
    result = AudioProcessor.frames_to_numpy(sample_audio_frames)
    
    # Check result
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.int16
    assert len(result) == 8
    assert result[0] == 0 and result[4] == 400

def test_frames_to_numpy_empty():
    """Test conversion of empty audio frames list"""
    result = AudioProcessor.frames_to_numpy([])
    assert isinstance(result, np.ndarray)
    assert len(result) == 0

def test_calculate_volume():
    """Test volume level calculation"""
    # Test with silence (zeros)
    silence = np.zeros(1000, dtype=np.int16)
    silence_volume = AudioProcessor.calculate_volume(silence)
    assert silence_volume == 0.0
    
    # Test with maximum volume
    max_volume = np.ones(1000, dtype=np.int16) * 32767  # Max value for int16
    max_volume_level = AudioProcessor.calculate_volume(max_volume)
    assert max_volume_level > 0.9
    
    # Test with medium volume
    medium_volume = np.ones(1000, dtype=np.int16) * 16384  # Half of max value
    medium_volume_level = AudioProcessor.calculate_volume(medium_volume)
    assert 0.4 < medium_volume_level < 0.6

def test_calculate_volume_empty():
    """Test volume calculation with empty array"""
    empty = np.array([], dtype=np.int16)
    volume = AudioProcessor.calculate_volume(empty)
    assert volume == 0.0

def test_resample_audio(sine_wave_audio):
    """Test audio resampling"""
    test_signal, original_rate = sine_wave_audio
    
    # Resample to Whisper's 16kHz
    target_rate = 16000
    resampled = AudioProcessor.resample_audio(test_signal, original_rate, target_rate)
    
    # Check result
    assert isinstance(resampled, np.ndarray)
    assert len(resampled) == int(len(test_signal) * target_rate / original_rate)
    
    # Test that resampling is a no-op when rates match
    same_rate = AudioProcessor.resample_audio(test_signal, original_rate, original_rate)
    assert len(same_rate) == len(test_signal)

def test_convert_to_whisper_format(sine_wave_audio):
    """Test conversion to Whisper format"""
    test_signal, original_rate = sine_wave_audio
    
    # Convert to Whisper format
    whisper_format = AudioProcessor.convert_to_whisper_format(test_signal, original_rate)
    
    # Check result
    assert isinstance(whisper_format, np.ndarray)
    assert whisper_format.dtype == np.float32
    expected_length = int(len(test_signal) * AudioProcessor.WHISPER_SAMPLE_RATE / original_rate)
    assert abs(len(whisper_format) - expected_length) <= 1  # Allow off-by-one due to rounding
    assert -1.0 <= whisper_format.max() <= 1.0
    assert -1.0 <= whisper_format.min() <= 1.0

def test_process_audio_for_transcription(sine_wave_audio):
    """Test the high-level audio processing function"""
    test_signal, original_rate = sine_wave_audio
    test_frames = [test_signal.tobytes()]
    
    # Process audio for transcription
    processed = AudioProcessor.process_audio_for_transcription(test_frames, original_rate)
    
    # Check result
    assert isinstance(processed, np.ndarray)
    assert processed.dtype == np.float32
    expected_length = int(len(test_signal) * AudioProcessor.WHISPER_SAMPLE_RATE / original_rate)
    assert abs(len(processed) - expected_length) <= 1  # Allow off-by-one due to rounding
    assert -1.0 <= processed.max() <= 1.0

def test_save_to_wav(sine_wave_audio):
    """Test saving audio data to WAV file"""
    test_signal, original_rate = sine_wave_audio
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Save to WAV file
        result = AudioProcessor.save_to_wav(test_signal, temp_path, original_rate)
        assert result
        
        # Check that file exists and has non-zero size
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
        
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_get_device_sample_rate():
    """Test mock for get_device_sample_rate"""
    # Create a mock audio instance
    class MockAudio:
        def get_default_input_device_info(self):
            return {'defaultSampleRate': 48000}
    
    mock_audio = MockAudio()
    
    # Test with device_info
    mock_device_info = {'defaultSampleRate': 44100}
    assert AudioProcessor.get_device_sample_rate(mock_audio, mock_device_info) == 44100
    
    # Test without device_info
    assert AudioProcessor.get_device_sample_rate(mock_audio) == 48000

def test_error_handling():
    """Test error handling in AudioProcessor methods"""
    # Test handling of invalid inputs
    invalid_signal = "not an array"
    
    # These should not raise exceptions but return sensible defaults
    assert AudioProcessor.calculate_volume(np.array([])) == 0.0
    
    # These should handle errors gracefully
    with pytest.raises(Exception):
        AudioProcessor.resample_audio(invalid_signal, 44100, 16000)
    
    with pytest.raises(Exception):
        AudioProcessor.convert_to_whisper_format(invalid_signal, 44100)
