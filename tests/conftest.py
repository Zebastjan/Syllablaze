"""
tests/conftest.py - Pytest configuration for Syllablaze tests

This file provides common fixtures and setup for all tests.
"""

import os
import sys
import pytest
import logging
import numpy as np

# Add parent directory to path to import modules from blaze
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging for tests
@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Mock PyAudio and related classes
class MockStream:
    """Mock PyAudio stream for testing"""
    def __init__(self):
        self.is_active = True
    
    def stop_stream(self):
        self.is_active = False
    
    def close(self):
        self.is_active = False

class MockPyAudio:
    """Mock PyAudio instance for testing"""
    def __init__(self):
        self.streams = []
    
    def get_device_info_by_index(self, index):
        return {
            'name': f'Test Device {index}',
            'defaultSampleRate': 44100,
            'maxInputChannels': 2,
            'index': index
        }
    
    def get_default_input_device_info(self):
        return self.get_device_info_by_index(0)
    
    def get_device_count(self):
        return 3
    
    def get_sample_size(self, format_type):
        return 2
    
    def open(self, **kwargs):
        stream = MockStream()
        self.streams.append(stream)
        return stream
    
    def terminate(self):
        for stream in self.streams:
            stream.close()
        self.streams = []

@pytest.fixture
def mock_pyaudio():
    """Fixture providing a mock PyAudio instance"""
    return MockPyAudio()

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
    # 440 Hz sine wave (A4 note)
    test_signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    return test_signal, sample_rate

# Mock for settings
class MockSettings:
    """Mock Settings class for testing"""
    def __init__(self):
        self.settings = {}
        
    def get(self, key, default=None):
        return self.settings.get(key, default)
        
    def set(self, key, value):
        self.settings[key] = value

@pytest.fixture
def mock_settings():
    """Fixture providing a mock Settings instance"""
    return MockSettings()
