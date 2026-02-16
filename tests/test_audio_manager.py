"""
Tests for the AudioManager class

Tests cover:
- Initialization
- Start/stop recording with mocks
- State transitions
- Error handling
- Recording lock management
- Cleanup
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QObject

from blaze.managers.audio_manager import AudioManager


@pytest.fixture
def mock_settings():
    """Create a mock Settings instance"""
    settings = Mock()
    settings.get = Mock(return_value=None)
    settings.set = Mock()
    return settings


@pytest.fixture
def mock_recorder():
    """Create a mock AudioRecorder instance"""
    recorder = Mock()
    recorder.volume_changing = MagicMock()
    recorder.audio_samples_changing = MagicMock()
    recorder.recording_completed = MagicMock()
    recorder.recording_failed = MagicMock()
    recorder.start_recording = Mock()
    recorder._stop_recording = Mock()
    recorder.cleanup = Mock()

    # Make signals connectable
    recorder.volume_changing.connect = Mock()
    recorder.audio_samples_changing.connect = Mock()
    recorder.recording_completed.connect = Mock()
    recorder.recording_failed.connect = Mock()

    return recorder


@pytest.fixture
def audio_manager(mock_settings):
    """Create an AudioManager instance for testing"""
    manager = AudioManager(mock_settings)
    return manager


def test_audio_manager_initialization(mock_settings):
    """Test AudioManager initialization"""
    manager = AudioManager(mock_settings)
    assert manager.settings == mock_settings
    assert manager.recorder is None
    assert manager.is_recording is False
    assert manager._recording_lock is False


def test_initialize_success(audio_manager, mock_recorder):
    """Test successful audio manager initialization"""
    with patch('blaze.recorder.AudioRecorder', return_value=mock_recorder):
        result = audio_manager.initialize()

        assert result is True
        assert audio_manager.recorder == mock_recorder

        # Verify signals were connected
        mock_recorder.volume_changing.connect.assert_called_once()
        mock_recorder.audio_samples_changing.connect.assert_called_once()
        mock_recorder.recording_completed.connect.assert_called_once()
        mock_recorder.recording_failed.connect.assert_called_once()


def test_initialize_failure(audio_manager):
    """Test audio manager initialization failure"""
    with patch('blaze.recorder.AudioRecorder', side_effect=Exception("Initialization failed")):
        result = audio_manager.initialize()

        assert result is False
        assert audio_manager.recorder is None


def test_start_recording_success(audio_manager, mock_recorder):
    """Test successful recording start"""
    audio_manager.recorder = mock_recorder

    result = audio_manager.start_recording()

    assert result is True
    assert audio_manager.is_recording is True
    mock_recorder.start_recording.assert_called_once()


def test_start_recording_without_initialization(audio_manager):
    """Test starting recording without initialization"""
    # recorder is None
    result = audio_manager.start_recording()

    assert result is False
    assert audio_manager.is_recording is False


def test_start_recording_already_recording(audio_manager, mock_recorder):
    """Test starting recording when already recording"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = True

    result = audio_manager.start_recording()

    # Should return True but not call start_recording again
    assert result is True
    mock_recorder.start_recording.assert_not_called()


def test_start_recording_with_exception(audio_manager, mock_recorder):
    """Test handling of exception during recording start"""
    audio_manager.recorder = mock_recorder
    mock_recorder.start_recording.side_effect = Exception("Recording start failed")

    result = audio_manager.start_recording()

    assert result is False
    assert audio_manager.is_recording is False


def test_stop_recording_success(audio_manager, mock_recorder):
    """Test successful recording stop"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = True

    result = audio_manager.stop_recording()

    assert result is True
    assert audio_manager.is_recording is False
    mock_recorder._stop_recording.assert_called_once()


def test_stop_recording_without_initialization(audio_manager):
    """Test stopping recording without initialization"""
    # recorder is None
    result = audio_manager.stop_recording()

    assert result is False


def test_stop_recording_not_recording(audio_manager, mock_recorder):
    """Test stopping recording when not recording"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = False

    result = audio_manager.stop_recording()

    # Should return True but not call _stop_recording
    assert result is True
    mock_recorder._stop_recording.assert_not_called()


def test_stop_recording_with_exception(audio_manager, mock_recorder):
    """Test handling of exception during recording stop"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = True
    mock_recorder._stop_recording.side_effect = Exception("Recording stop failed")

    result = audio_manager.stop_recording()

    assert result is False
    # is_recording should remain True since stop failed
    assert audio_manager.is_recording is True


def test_save_audio_to_file_success(audio_manager):
    """Test successful audio file saving"""
    audio_data = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    filename = '/tmp/test.wav'

    with patch('blaze.managers.audio_manager.AudioProcessor.save_to_wav', return_value=True):
        result = audio_manager.save_audio_to_file(audio_data, filename)

        assert result is True


def test_save_audio_to_file_failure(audio_manager):
    """Test audio file saving failure"""
    audio_data = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    filename = '/tmp/test.wav'

    with patch('blaze.managers.audio_manager.AudioProcessor.save_to_wav', return_value=False):
        result = audio_manager.save_audio_to_file(audio_data, filename)

        assert result is False


def test_save_audio_to_file_with_exception(audio_manager):
    """Test handling of exception during file saving"""
    audio_data = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    filename = '/tmp/test.wav'

    with patch('blaze.managers.audio_manager.AudioProcessor.save_to_wav', side_effect=Exception("Save failed")):
        result = audio_manager.save_audio_to_file(audio_data, filename)

        assert result is False


def test_is_ready_to_record_success(audio_manager):
    """Test is_ready_to_record with valid transcription manager"""
    # Create a mock transcription manager with all required attributes
    transcription_manager = Mock()
    transcription_manager.transcriber = Mock()
    transcription_manager.transcriber.model = Mock()

    app_state = Mock()
    app_state.is_transcribing.return_value = False

    ready, error = audio_manager.is_ready_to_record(transcription_manager, app_state)

    assert ready is True
    assert error == ""


def test_is_ready_to_record_already_transcribing(audio_manager):
    """Test is_ready_to_record when already transcribing"""
    transcription_manager = Mock()
    app_state = Mock()
    app_state.is_transcribing.return_value = True

    ready, error = audio_manager.is_ready_to_record(transcription_manager, app_state)

    assert ready is False
    assert "transcription is in progress" in error


def test_is_ready_to_record_no_transcription_manager(audio_manager):
    """Test is_ready_to_record without transcription manager"""
    ready, error = audio_manager.is_ready_to_record(None)

    assert ready is False
    assert "not initialized" in error


def test_is_ready_to_record_no_transcriber(audio_manager):
    """Test is_ready_to_record without transcriber"""
    transcription_manager = Mock()
    transcription_manager.transcriber = None

    ready, error = audio_manager.is_ready_to_record(transcription_manager)

    assert ready is False
    assert "not initialized" in error


def test_is_ready_to_record_no_model(audio_manager):
    """Test is_ready_to_record without model loaded"""
    transcription_manager = Mock()
    transcription_manager.transcriber = Mock()
    transcription_manager.transcriber.model = None

    ready, error = audio_manager.is_ready_to_record(transcription_manager)

    assert ready is False
    assert "No Whisper model loaded" in error


def test_acquire_recording_lock_success(audio_manager):
    """Test successful recording lock acquisition"""
    result = audio_manager.acquire_recording_lock()

    assert result is True
    assert audio_manager._recording_lock is True


def test_acquire_recording_lock_already_locked(audio_manager):
    """Test acquiring lock when already locked"""
    audio_manager._recording_lock = True

    result = audio_manager.acquire_recording_lock()

    assert result is False


def test_release_recording_lock(audio_manager):
    """Test releasing recording lock"""
    audio_manager._recording_lock = True

    audio_manager.release_recording_lock()

    assert audio_manager._recording_lock is False


def test_cleanup_success(audio_manager, mock_recorder):
    """Test successful cleanup"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = False

    result = audio_manager.cleanup()

    assert result is True
    assert audio_manager.recorder is None
    mock_recorder.cleanup.assert_called_once()


def test_cleanup_while_recording(audio_manager, mock_recorder):
    """Test cleanup while recording"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = True

    result = audio_manager.cleanup()

    assert result is True
    assert audio_manager.recorder is None
    # Should have stopped recording first
    mock_recorder._stop_recording.assert_called_once()
    mock_recorder.cleanup.assert_called_once()


def test_cleanup_without_recorder(audio_manager):
    """Test cleanup without recorder"""
    audio_manager.recorder = None

    result = audio_manager.cleanup()

    assert result is True


def test_cleanup_with_exception(audio_manager, mock_recorder):
    """Test cleanup with exception"""
    audio_manager.recorder = mock_recorder
    mock_recorder.cleanup.side_effect = Exception("Cleanup failed")

    result = audio_manager.cleanup()

    assert result is False


def test_recording_state_transitions(audio_manager, mock_recorder):
    """Test state transitions during recording lifecycle"""
    audio_manager.recorder = mock_recorder

    # Initial state
    assert audio_manager.is_recording is False

    # Start recording
    audio_manager.start_recording()
    assert audio_manager.is_recording is True

    # Stop recording
    audio_manager.stop_recording()
    assert audio_manager.is_recording is False


def test_on_recording_completed_signal(audio_manager, mock_recorder):
    """Test that _on_recording_completed emits signal"""
    audio_data = np.array([1, 2, 3], dtype=np.int16)

    # Connect a spy to recording_completed signal
    signal_spy = Mock()
    audio_manager.recording_completed.connect(signal_spy)

    # Trigger the internal handler
    audio_manager._on_recording_completed(audio_data)

    # Verify signal was emitted with correct data
    signal_spy.assert_called_once()
    call_args = signal_spy.call_args[0]
    assert np.array_equal(call_args[0], audio_data)


def test_start_recording_timeout_warning(audio_manager, mock_recorder):
    """Test warning when recording start takes too long"""
    audio_manager.recorder = mock_recorder

    # Mock start_recording to simulate slow start
    def slow_start():
        import time
        time.sleep(2.5)  # More than 2 seconds

    mock_recorder.start_recording = slow_start

    # Should still succeed but log warning
    result = audio_manager.start_recording()
    assert result is True


def test_stop_recording_timeout_warning(audio_manager, mock_recorder):
    """Test warning when recording stop takes too long"""
    audio_manager.recorder = mock_recorder
    audio_manager.is_recording = True

    # Mock _stop_recording to simulate slow stop
    def slow_stop():
        import time
        time.sleep(2.5)  # More than 2 seconds

    mock_recorder._stop_recording = slow_stop

    # Should still succeed but log warning
    result = audio_manager.stop_recording()
    assert result is True
