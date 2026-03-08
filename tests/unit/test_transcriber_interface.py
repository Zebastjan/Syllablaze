"""
Tests to ensure all transcriber implementations conform to BaseTranscriber interface.

These tests prevent regressions when adding new transcriber types by ensuring
all implementations follow the required interface contract.
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from blaze.transcriber_base import BaseTranscriber
from blaze.transcriber import WhisperTranscriber
from blaze.managers.coordinator_transcriber import CoordinatorTranscriber


class TestBaseTranscriberInterface:
    """Test that all transcriber implementations conform to the interface."""

    def test_whisper_transcriber_is_subclass(self):
        """Verify WhisperTranscriber inherits from BaseTranscriber."""
        assert issubclass(WhisperTranscriber, BaseTranscriber)

    def test_coordinator_transcriber_is_subclass(self):
        """Verify CoordinatorTranscriber inherits from BaseTranscriber."""
        assert issubclass(CoordinatorTranscriber, BaseTranscriber)

    def test_all_transcribers_have_required_methods(self):
        """Verify all transcribers implement required abstract methods."""
        required_methods = [
            "is_model_loaded",
            "update_model",
            "update_language",
            "transcribe_audio",
            "reload_model_if_needed",
        ]

        for cls in [WhisperTranscriber, CoordinatorTranscriber]:
            for method in required_methods:
                assert hasattr(cls, method), f"{cls.__name__} missing {method}"

    def test_all_transcribers_have_required_signals(self):
        """Verify all transcribers have required signals."""
        required_signals = [
            "transcription_progress",
            "transcription_progress_percent",
            "transcription_finished",
            "transcription_error",
            "model_changed",
            "language_changed",
        ]

        for cls in [WhisperTranscriber, CoordinatorTranscriber]:
            for signal in required_signals:
                assert hasattr(cls, signal), f"{cls.__name__} missing signal {signal}"


class TestTranscriberIsModelLoaded:
    """Test is_model_loaded() behavior across all transcriber types."""

    @patch("blaze.transcriber.WhisperModelManager")
    def test_whisper_transcriber_is_model_loaded_true(self, mock_manager_class):
        """Test WhisperTranscriber.is_model_loaded() returns True when model loaded."""
        mock_settings = Mock()
        mock_manager = Mock()
        mock_manager.is_model_downloaded.return_value = False  # Don't actually load
        mock_manager_class.return_value = mock_manager

        transcriber = WhisperTranscriber(load_model=False)
        transcriber.model = Mock()  # Simulate loaded model

        assert transcriber.is_model_loaded() is True

    @patch("blaze.transcriber.WhisperModelManager")
    def test_whisper_transcriber_is_model_loaded_false(self, mock_manager_class):
        """Test WhisperTranscriber.is_model_loaded() returns False when no model."""
        mock_settings = Mock()
        mock_manager = Mock()
        mock_manager.is_model_downloaded.return_value = False
        mock_manager_class.return_value = mock_manager

        transcriber = WhisperTranscriber(load_model=False)
        transcriber.model = None

        assert transcriber.is_model_loaded() is False

    def test_coordinator_transcriber_is_model_loaded_true(self):
        """Test CoordinatorTranscriber.is_model_loaded() returns True when model loaded."""
        mock_settings = Mock()
        mock_settings.get.return_value = "granite-speech-3.3-2b"

        transcriber = CoordinatorTranscriber(mock_settings)
        transcriber._current_model_name = "granite-speech-3.3-2b"

        assert transcriber.is_model_loaded() is True

    def test_coordinator_transcriber_is_model_loaded_false(self):
        """Test CoordinatorTranscriber.is_model_loaded() returns False when no model."""
        mock_settings = Mock()
        mock_settings.get.return_value = None

        transcriber = CoordinatorTranscriber(mock_settings)
        # _current_model_name remains None

        assert transcriber.is_model_loaded() is False


class TestTranscriptionManagerAbstraction:
    """Test that TranscriptionManager properly abstracts transcriber differences."""

    def test_is_model_loaded_delegates_to_transcriber(self):
        """Verify TranscriptionManager.is_model_loaded() works with both transcriber types."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)

        # Test with WhisperTranscriber-style transcriber
        whisper_transcriber = Mock()
        whisper_transcriber.is_model_loaded = Mock(return_value=True)
        manager.transcriber = whisper_transcriber

        assert manager.is_model_loaded() is True

        # Test with CoordinatorTranscriber-style transcriber
        coordinator_transcriber = Mock()
        coordinator_transcriber.is_model_loaded = Mock(return_value=True)
        manager.transcriber = coordinator_transcriber

        assert manager.is_model_loaded() is True

    def test_is_model_loaded_false_when_no_model(self):
        """Verify is_model_loaded() returns False when no model loaded."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)

        # Test with WhisperTranscriber with no model
        whisper_transcriber = Mock()
        whisper_transcriber.is_model_loaded = Mock(return_value=False)
        manager.transcriber = whisper_transcriber

        assert manager.is_model_loaded() is False

        # Test with CoordinatorTranscriber with no model
        coordinator_transcriber = Mock()
        coordinator_transcriber.is_model_loaded = Mock(return_value=False)
        manager.transcriber = coordinator_transcriber

        assert manager.is_model_loaded() is False


class TestAudioManagerIntegration:
    """Test that AudioManager works with both transcriber types."""

    @patch("blaze.managers.audio_manager.AudioManager.initialize")
    def test_is_ready_to_record_with_whisper_transcriber(self, mock_init):
        """Test is_ready_to_record with WhisperTranscriber-style transcriber."""
        from blaze.managers.audio_manager import AudioManager

        mock_settings = Mock()
        audio_manager = AudioManager(mock_settings)

        transcription_manager = Mock()
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = Mock()  # Whisper has .model
        transcription_manager.is_model_loaded = Mock(return_value=True)
        transcription_manager.is_worker_running = Mock(return_value=False)

        app_state = Mock()
        app_state.is_transcribing.return_value = False

        ready, error = audio_manager.is_ready_to_record(
            transcription_manager, app_state
        )

        assert ready is True
        assert error == ""

    @patch("blaze.managers.audio_manager.AudioManager.initialize")
    def test_is_ready_to_record_with_coordinator_transcriber(self, mock_init):
        """Test is_ready_to_record with CoordinatorTranscriber-style transcriber."""
        from blaze.managers.audio_manager import AudioManager

        mock_settings = Mock()
        audio_manager = AudioManager(mock_settings)

        transcription_manager = Mock()
        transcription_manager.transcriber = Mock()
        transcription_manager.transcriber.model = None  # Coordinator doesn't use .model
        transcription_manager.transcriber.current_model_name = "granite-speech-3.3-2b"
        transcription_manager.is_model_loaded = Mock(return_value=True)
        transcription_manager.is_worker_running = Mock(return_value=False)

        app_state = Mock()
        app_state.is_transcribing.return_value = False

        ready, error = audio_manager.is_ready_to_record(
            transcription_manager, app_state
        )

        # Should be True because is_model_loaded() returns True
        assert ready is True
        assert error == ""

    @patch("blaze.managers.audio_manager.AudioManager.initialize")
    def test_is_ready_to_record_fails_when_no_model(self, mock_init):
        """Test is_ready_to_record returns False when no model loaded."""
        from blaze.managers.audio_manager import AudioManager

        mock_settings = Mock()
        audio_manager = AudioManager(mock_settings)

        transcription_manager = Mock()
        transcription_manager.is_model_loaded = Mock(return_value=False)
        transcription_manager.is_worker_running = Mock(return_value=False)

        app_state = Mock()
        app_state.is_transcribing.return_value = False

        ready, error = audio_manager.is_ready_to_record(
            transcription_manager, app_state
        )

        assert ready is False
        assert "No model loaded" in error
