"""
Test Backend Switching Architecture - Option C Implementation

These tests ensure that:
1. Backend is ALWAYS derived from model_id, never from stored model_backend
2. Proper type checking is used (isinstance) instead of fragile hasattr
3. Backend health is tracked and reported to users
4. No auto-fallback - users see clear errors and can select different models
5. Each backend works independently - failure in one doesn't break others
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import numpy as np


class TestBackendDerivation:
    """Test that backend is always derived from model_id."""

    def test_backend_derived_from_model_id(self):
        """Backend should be derived from model_id, not stored setting."""
        from blaze.backends.registry import ModelRegistry

        # Test that get_backend_for_model works for all model types
        assert ModelRegistry.get_backend_for_model("whisper-base") == "whisper"
        assert ModelRegistry.get_backend_for_model("whisper-large-v3") == "whisper"
        assert ModelRegistry.get_backend_for_model("lfm2.5-audio-1.5b") == "liquid"
        assert ModelRegistry.get_backend_for_model("granite-speech-3.3-2b") == "granite"

    def test_backend_default_to_whisper_for_unknown(self):
        """Unknown models should return None, handled by caller with default."""
        from blaze.backends.registry import ModelRegistry

        # Unknown models return None
        assert ModelRegistry.get_backend_for_model("unknown-model") is None
        assert ModelRegistry.get_backend_for_model("nonexistent") is None

        # Factory handles None by defaulting to whisper
        from blaze.managers.transcription_manager import TranscriberFactory

        assert TranscriberFactory.get_backend_for_model("unknown-model") == "whisper"


class TestTranscriberTypeDetection:
    """Test that transcriber type is detected properly."""

    def test_whisper_transcriber_detected_correctly(self):
        """WhisperTranscriber should be detected via isinstance."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)

        # Create a mock that passes isinstance check
        mock_transcriber = Mock(spec=WhisperTranscriber)
        manager.transcriber = mock_transcriber
        transcriber_type = manager._get_transcriber_type()

        assert transcriber_type == "whisper"

    def test_coordinator_transcriber_detected_correctly(self):
        """CoordinatorTranscriber should be detected via isinstance."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.managers.coordinator_transcriber import CoordinatorTranscriber

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)

        # Create a mock that passes isinstance check
        mock_transcriber = Mock(spec=CoordinatorTranscriber)
        manager.transcriber = mock_transcriber
        transcriber_type = manager._get_transcriber_type()

        assert transcriber_type == "coordinator"

    def test_dummy_transcriber_detected_correctly(self):
        """DummyTranscriber should be detected via _is_dummy_transcriber marker."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)

        # Create a dummy transcriber
        manager._create_dummy_transcriber("liquid", "Test error")
        transcriber_type = manager._get_transcriber_type()

        assert transcriber_type == "dummy"


class TestBackendHealthTracking:
    """Test that backend health is tracked properly."""

    def test_backend_health_tracked_on_failure(self):
        """Backend health should be updated when initialization fails."""
        from blaze.backends.backend_health import (
            BackendHealthRegistry,
            BackendHealthStatus,
        )

        registry = BackendHealthRegistry()

        # Simulate a failed initialization
        registry.update_status(
            "liquid", BackendHealthStatus.FAILED, "Dependency not installed"
        )

        assert registry.is_failed("liquid") is True
        assert registry.get_status("liquid") == BackendHealthStatus.FAILED
        assert registry.get_last_error("liquid") == "Dependency not installed"

    def test_backend_health_cleared_on_success(self):
        """Backend health should be updated on successful initialization."""
        from blaze.backends.backend_health import (
            BackendHealthRegistry,
            BackendHealthStatus,
        )

        registry = BackendHealthRegistry()

        # First fail, then succeed
        registry.update_status("liquid", BackendHealthStatus.FAILED, "Error")
        registry.update_status("liquid", BackendHealthStatus.HEALTHY)

        assert registry.is_failed("liquid") is False
        assert registry.is_healthy("liquid") is True


class TestNoAutoFallback:
    """Test that there is NO auto-fallback to whisper."""

    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_failed_backend_creates_dummy_not_whisper_fallback(self, mock_check_gpu):
        """When backend fails, should create dummy, not auto-fallback to whisper."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "model": "lfm2.5-audio-1.5b",  # Liquid model
            "language": "auto",
        }.get(key, default)

        # Make CoordinatorTranscriber fail
        with patch(
            "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
        ) as mock_coordinator:
            mock_coordinator.side_effect = ImportError("liquid module not installed")

            manager = TranscriptionManager(mock_settings)
            result = manager.initialize()

            # Should fail, not fallback
            assert result is False

            # Should have dummy transcriber, not whisper
            assert manager._get_transcriber_type() == "dummy"

            # Should emit backend error signal
            # Note: We can't easily test signal emission here, but the code does emit it

    def test_dummy_transcriber_shows_clear_error(self):
        """Dummy transcriber should show clear error message to user."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)

        # Create dummy transcriber
        manager._create_dummy_transcriber(
            "liquid", "ImportError: No module named 'liquid'"
        )

        # Try to transcribe - should emit clear error
        errors = []
        manager.transcription_error.connect(lambda msg: errors.append(msg))
        manager.transcriber.transcribe_audio(np.array([0.1, 0.2]))

        # Should have emitted error with backend name
        assert len(errors) == 1
        assert "Liquid" in errors[0]
        assert "select a different model" in errors[0].lower()


class TestBackendIsolation:
    """Test that backends are properly isolated."""

    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_switching_from_failed_to_working_backend(self, mock_check_gpu):
        """Should be able to switch from failed backend to working one."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_settings = Mock()
        # Use a lambda to return different values based on call count
        call_count = [0]

        def side_effect_func(key, default=None):
            call_count[0] += 1
            # First initialize() calls: model=lfm2.5-audio-1.5b, language=auto
            # Second initialize() calls: model=whisper-base, language=auto
            if call_count[0] <= 4:
                # First batch (liquid - will fail)
                return {"model": "lfm2.5-audio-1.5b", "language": "auto"}.get(
                    key, default
                )
            else:
                # Second batch (whisper - will succeed)
                return {"model": "whisper-base", "language": "auto"}.get(key, default)

        mock_settings.get.side_effect = side_effect_func

        with patch(
            "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
        ) as mock_coordinator:
            mock_coordinator.side_effect = ImportError("liquid module not installed")

            with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
                # Create a spec'd mock that passes isinstance check
                mock_whisper_instance = Mock(spec=WhisperTranscriber)
                mock_whisper_instance.is_model_loaded.return_value = True
                mock_whisper.return_value = mock_whisper_instance

                # First: Try to initialize with Liquid (will fail)
                manager = TranscriptionManager(mock_settings)
                result = manager.initialize()
                assert result is False  # Should fail
                assert manager._get_transcriber_type() == "dummy"

                # Second: Switch to Whisper model (should succeed after cleanup/reinit)
                # Note: In real app, this would be triggered by user selecting different model
                # For test, we manually trigger cleanup and reinit
                manager.cleanup()
                result = manager.initialize()
                assert result is True  # Should succeed
                assert manager._get_transcriber_type() == "whisper"


class TestProperErrorMessages:
    """Test that users get clear error messages."""

    def test_get_model_status_shows_clear_message_for_dummy(self):
        """get_model_status should show clear message when backend failed."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        manager = TranscriptionManager(mock_settings)
        manager._create_dummy_transcriber(
            "liquid", "ImportError: No module named 'liquid'"
        )

        status = manager.get_model_status()

        assert (
            "failed" in status.lower() or "select a different model" in status.lower()
        )


class TestTranscriberFactory:
    """Test TranscriberFactory for proper backend routing."""

    def test_factory_creates_whisper_transcriber(self):
        """Factory should create WhisperTranscriber for whisper backend."""
        from blaze.managers.transcription_manager import TranscriberFactory

        with patch("blaze.transcriber.WhisperTranscriber") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            transcriber = TranscriberFactory.create_transcriber("whisper", Mock())

            mock_class.assert_called_once()
            assert transcriber is mock_instance

    def test_factory_creates_coordinator_for_liquid(self):
        """Factory should create CoordinatorTranscriber for liquid backend."""
        from blaze.managers.transcription_manager import TranscriberFactory

        mock_settings = Mock()

        with patch(
            "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
        ) as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            transcriber = TranscriberFactory.create_transcriber("liquid", mock_settings)

            mock_class.assert_called_once_with(mock_settings)
            assert transcriber is mock_instance

    def test_factory_creates_coordinator_for_granite(self):
        """Factory should create CoordinatorTranscriber for granite backend."""
        from blaze.managers.transcription_manager import TranscriberFactory

        mock_settings = Mock()

        with patch(
            "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
        ) as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            transcriber = TranscriberFactory.create_transcriber(
                "granite", mock_settings
            )

            mock_class.assert_called_once_with(mock_settings)
            assert transcriber is mock_instance

    def test_factory_raises_error_for_unknown_backend(self):
        """Factory should raise error for unknown backend type."""
        from blaze.managers.transcription_manager import TranscriberFactory

        with pytest.raises(ValueError) as exc_info:
            TranscriberFactory.create_transcriber("unknown-backend", Mock())

        assert "Unknown backend" in str(exc_info.value)


class TestCheckBackendChange:
    """Test the _check_backend_change method."""

    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_backend_change_detected_from_model(self, mock_check_gpu):
        """Should detect backend change when model_id changes."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber
        from blaze.managers.coordinator_transcriber import CoordinatorTranscriber

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_settings = Mock()
        # Start with whisper model, then switch to liquid
        call_count = [0]

        def side_effect_func(key, default=None):
            call_count[0] += 1
            # First initialize() calls: model=whisper-base (calls 1-5)
            # _check_backend_change() call 6 should return liquid model
            # Second initialize() calls: model=lfm2.5-audio-1.5b (calls 7+)
            if call_count[0] <= 5:
                return {"model": "whisper-base", "language": "auto"}.get(key, default)
            else:
                return {"model": "lfm2.5-audio-1.5b", "language": "auto"}.get(
                    key, default
                )

        mock_settings.get.side_effect = side_effect_func

        with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
            # Create a spec'd mock that passes isinstance check
            mock_whisper_instance = Mock(spec=WhisperTranscriber)
            mock_whisper_instance.is_model_loaded.return_value = True
            mock_whisper.return_value = mock_whisper_instance

            # Initialize with whisper
            manager = TranscriptionManager(mock_settings)
            manager.initialize()
            assert manager._get_transcriber_type() == "whisper"

            # Now change to liquid model
            with patch(
                "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
            ) as mock_coordinator:
                # Create a spec'd mock that passes isinstance check
                mock_coordinator_instance = Mock(spec=CoordinatorTranscriber)
                mock_coordinator_instance.is_model_loaded.return_value = True
                mock_coordinator.return_value = mock_coordinator_instance

                # Trigger backend change check
                result = manager._check_backend_change()

                # Should have reinitialized for liquid
                assert result is True
                assert manager._get_transcriber_type() == "coordinator"
