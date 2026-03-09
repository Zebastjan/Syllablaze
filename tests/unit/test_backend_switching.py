"""
Test Backend Switching Architecture

These tests ensure that:
1. Backend selection works correctly based on model ID
2. Model loading happens during initialization (eager loading)
3. Recording starts successfully when model is loaded (no settings window popup)
4. Backends are properly isolated and don't interfere with each other
5. Backend naming doesn't collide (whisper vs faster-whisper)
6. Switching between backends properly unloads previous backend
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import numpy as np


class TestBackendSelection:
    """Test that correct backend is selected based on model ID."""

    def test_whisper_backend_selected_for_whisper_models(self):
        """Whisper backend should be selected for whisper-* model IDs."""
        from blaze.backends.registry import ModelRegistry

        # Test various Whisper model IDs
        whisper_models = [
            "whisper-tiny",
            "whisper-base",
            "whisper-small",
            "whisper-medium",
            "whisper-large-v1",
            "whisper-large-v2",
            "whisper-large-v3",
            "whisper-large-v3-turbo",
            "whisper-distil-large-v2",
        ]

        for model_id in whisper_models:
            model_info = ModelRegistry.get_model(model_id)
            if model_info:
                assert model_info.backend == "whisper", (
                    f"{model_id} should use whisper backend"
                )

    def test_liquid_backend_selected_for_liquid_models(self):
        """Liquid backend should be selected for lfm2.5-* model IDs."""
        from blaze.backends.registry import ModelRegistry

        liquid_models = [
            "lfm2.5-audio-1.5b",
        ]

        for model_id in liquid_models:
            model_info = ModelRegistry.get_model(model_id)
            if model_info:
                assert model_info.backend == "liquid", (
                    f"{model_id} should use liquid backend"
                )

    def test_granite_backend_selected_for_granite_models(self):
        """Granite backend should be selected for granite-* model IDs."""
        from blaze.backends.registry import ModelRegistry

        granite_models = [
            "granite-speech-3.3-2b",
        ]

        for model_id in granite_models:
            model_info = ModelRegistry.get_model(model_id)
            if model_info:
                assert model_info.backend == "granite", (
                    f"{model_id} should use granite backend"
                )

    def test_backend_type_derived_from_model_id(self):
        """Backend type should be derived from model_id, not stored separately."""
        from blaze.backends.registry import ModelRegistry

        # Should be able to determine backend from model_id alone
        model_id = "whisper-large-v3"
        backend = ModelRegistry.get_backend_for_model(model_id)
        assert backend == "whisper"

        model_id = "granite-speech-3.3-2b"
        backend = ModelRegistry.get_backend_for_model(model_id)
        assert backend == "granite"


class TestEagerModelLoading:
    """Test that models are loaded eagerly during initialization."""

    @patch("blaze.transcriber.WhisperTranscriber")
    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_model_loaded_during_initialize(
        self, mock_check_gpu, mock_transcriber_class
    ):
        """Model should be loaded when initialize() is called."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "model": "whisper-base",
            "language": "auto",
        }.get(key, default)

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_transcriber = Mock()
        mock_transcriber.is_model_loaded.return_value = True
        mock_transcriber_class.return_value = mock_transcriber

        manager = TranscriptionManager(mock_settings)
        result = manager.initialize()

        assert result is True
        # Transcriber should be created and model should be loaded
        assert manager.transcriber is not None
        assert manager.transcriber.is_model_loaded() is True

    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_initialize_fails_when_model_cannot_load(self, mock_check_gpu):
        """initialize() should fail if model cannot be loaded."""
        from blaze.managers.transcription_manager import TranscriptionManager

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "model": "whisper-base",
            "language": "auto",
        }.get(key, default)

        mock_check_gpu.return_value = (False, "Not enough GPU memory")

        manager = TranscriptionManager(mock_settings)
        result = manager.initialize()

        assert result is False
        # Should create dummy transcriber when initialization fails
        assert manager.transcriber is not None

    def test_is_model_loaded_true_after_initialize(self):
        """is_model_loaded() should return True immediately after successful initialize()."""
        from blaze.managers.transcription_manager import TranscriptionManager

        with patch.object(
            TranscriptionManager, "check_gpu_memory", return_value=(True, "OK")
        ):
            with patch("blaze.transcriber.WhisperTranscriber") as mock_class:
                mock_transcriber = Mock()
                mock_transcriber.is_model_loaded.return_value = True
                mock_class.return_value = mock_transcriber

                mock_settings = Mock()
                mock_settings.get.side_effect = lambda key, default=None: {
                    "model": "whisper-base",
                    "language": "auto",
                }.get(key, default)

                manager = TranscriptionManager(mock_settings)
                manager.initialize()

                # Immediately after initialize, model should be loaded
                assert manager.is_model_loaded() is True


class TestRecordingFlow:
    """Test that recording starts successfully when model is loaded."""

    @patch("blaze.managers.audio_manager.AudioManager.initialize")
    def test_recording_starts_when_model_loaded(self, mock_init):
        """Recording should start successfully when model is loaded."""
        from blaze.managers.audio_manager import AudioManager

        mock_settings = Mock()
        audio_manager = AudioManager(mock_settings)

        # Mock transcription manager with loaded model
        transcription_manager = Mock()
        transcription_manager.is_model_loaded.return_value = True
        transcription_manager.is_worker_running.return_value = False
        transcription_manager.transcriber = Mock()

        app_state = Mock()
        app_state.is_transcribing.return_value = False

        ready, error = audio_manager.is_ready_to_record(
            transcription_manager, app_state
        )

        assert ready is True, f"Should be ready to record, but got error: {error}"
        assert error == ""

    @patch("blaze.managers.audio_manager.AudioManager.initialize")
    def test_no_settings_window_when_model_loaded(self, mock_init):
        """Settings window should NOT open when model is properly loaded and user presses shortcut."""
        from blaze.managers.audio_manager import AudioManager

        mock_settings = Mock()
        audio_manager = AudioManager(mock_settings)

        # Simulate loaded model scenario
        transcription_manager = Mock()
        transcription_manager.is_model_loaded.return_value = True
        transcription_manager.is_worker_running.return_value = False
        transcription_manager.transcriber = Mock()

        app_state = Mock()
        app_state.is_transcribing.return_value = False

        ready, error = audio_manager.is_ready_to_record(
            transcription_manager, app_state
        )

        # Should be ready, no error about model
        assert ready is True
        assert "model" not in error.lower()
        assert "settings" not in error.lower()


class TestBackendIsolation:
    """Test that backends are properly isolated."""

    def test_each_backend_instance_isolated(self):
        """Each backend instance should be independent."""
        from blaze.backends.coordinator import BackendCoordinator

        # Create two separate coordinator instances
        coordinator1 = BackendCoordinator()
        coordinator2 = BackendCoordinator()

        # They should be independent (not singletons)
        assert coordinator1 is not coordinator2

    def test_switching_backends_unloads_previous(self):
        """When switching backends, previous backend should be unloaded."""
        from blaze.backends.coordinator import BackendCoordinator

        coordinator = BackendCoordinator()

        # Create mock backends that simulate real backends
        mock_whisper_backend = Mock()
        mock_whisper_backend.load = Mock()
        mock_whisper_backend.unload = Mock()

        mock_liquid_backend = Mock()
        mock_liquid_backend.load = Mock()
        mock_liquid_backend.unload = Mock()

        # Inject mock backends into coordinator
        coordinator._backends["whisper"] = lambda: mock_whisper_backend
        coordinator._backends["liquid"] = lambda: mock_liquid_backend

        # Load whisper backend
        coordinator.load_model("whisper-base")

        # Switch to liquid backend
        coordinator.load_model("lfm2.5-audio-1.5b")

        # Old backend should be unloaded
        mock_whisper_backend.unload.assert_called_once()

    @patch("blaze.managers.transcription_manager.TranscriptionManager.cleanup")
    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_cleanup_called_when_switching_models(self, mock_check_gpu, mock_cleanup):
        """cleanup() should be called when switching between models."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "model": "granite-speech-3.3-2b",  # Different from whisper-base
            "language": "auto",
        }.get(key, default)

        # Initialize with whisper-base first
        with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
            mock_whisper_instance = Mock(spec=WhisperTranscriber)
            mock_whisper_instance.is_model_loaded.return_value = True
            mock_whisper.return_value = mock_whisper_instance

            manager = TranscriptionManager(mock_settings)
            manager.current_model = (
                "whisper-base"  # Set current model to trigger change
            )
            manager.transcriber = (
                mock_whisper_instance  # Set transcriber to whisper type
            )

            # This should trigger cleanup of old model
            manager._check_backend_change()

            # Cleanup should be called
            mock_cleanup.assert_called_once()


class TestBackendNaming:
    """Test that backend naming doesn't collide."""

    def test_whisper_vs_faster_whisper_different_backends(self):
        """Whisper and faster-whisper should be distinguishable."""
        from blaze.backends.registry import ModelRegistry

        # Both should map to 'whisper' backend for now, but models should be distinct
        whisper_models = ModelRegistry.get_models_for_backend("whisper")
        model_ids = [m.model_id for m in whisper_models]

        # Should have both regular whisper and distil-whisper models
        assert any("whisper-" in m for m in model_ids)

    def test_model_ids_unique_across_backends(self):
        """All model IDs should be unique across all backends."""
        from blaze.backends.registry import ModelRegistry

        all_models = ModelRegistry.get_all_models()
        model_ids = [m.model_id for m in all_models]

        # No duplicates
        assert len(model_ids) == len(set(model_ids)), (
            f"Duplicate model IDs found: {[m for m in model_ids if model_ids.count(m) > 1]}"
        )

    def test_backend_names_distinct(self):
        """Backend names should be distinct and not overlap."""
        from blaze.backends.registry import ModelRegistry

        backends = ModelRegistry.get_available_backends()
        # get_available_backends returns a list of strings
        backend_names = backends

        # No duplicates
        assert len(backend_names) == len(set(backend_names))


class TestBackendSwitchingIntegration:
    """Integration tests for backend switching."""

    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_switch_whisper_to_liquid_and_back(self, mock_check_gpu):
        """Test switching from Whisper to Liquid and back to Whisper."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_settings = Mock()
        # Use call counting to switch models
        call_count = [0]

        def side_effect_func(key, default=None):
            call_count[0] += 1
            # First batch: whisper-base (calls 1-5)
            # After _check_backend_change: lfm2.5-audio-1.5b (calls 6+)
            if call_count[0] <= 5:
                return {"model": "whisper-base", "language": "auto"}.get(key, default)
            else:
                return {"model": "lfm2.5-audio-1.5b", "language": "auto"}.get(
                    key, default
                )

        mock_settings.get.side_effect = side_effect_func

        with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
            with patch(
                "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
            ) as mock_coordinator:
                # Create spec'd mock with cleanup method
                mock_whisper_instance = Mock(spec=WhisperTranscriber)
                mock_whisper_instance.is_model_loaded.return_value = True
                mock_whisper_instance.cleanup = Mock()
                mock_whisper.return_value = mock_whisper_instance

                mock_coordinator_instance = Mock()
                mock_coordinator_instance.is_model_loaded.return_value = True
                mock_coordinator_instance.cleanup = Mock()
                mock_coordinator.return_value = mock_coordinator_instance

                # Initialize with whisper
                manager = TranscriptionManager(mock_settings)
                manager.initialize()

                assert manager.transcriber is mock_whisper_instance

                # Switch to liquid
                manager._check_backend_change()

                # Should now have coordinator transcriber
                assert manager.transcriber is mock_coordinator_instance

                # Whisper transcriber should be cleaned up
                mock_whisper_instance.cleanup.assert_called_once()

    def test_transcription_works_after_backend_switch(self):
        """Transcription should work correctly after switching backends."""
        from blaze.managers.transcription_manager import TranscriptionManager

        with patch.object(
            TranscriptionManager, "check_gpu_memory", return_value=(True, "OK")
        ):
            mock_settings = Mock()
            mock_settings.get.side_effect = lambda key, default=None: {
                "model": "whisper-base",
                "language": "auto",
            }.get(key, default)

            with patch("blaze.transcriber.WhisperTranscriber") as mock_class:
                mock_transcriber = Mock()
                mock_transcriber.is_model_loaded.return_value = True
                mock_transcriber.transcribe_audio = Mock()
                mock_class.return_value = mock_transcriber

                manager = TranscriptionManager(mock_settings)
                manager.initialize()

                # Simulate transcription
                audio_data = np.array([0.1, 0.2, 0.3])
                manager.transcribe_audio(audio_data)

                # Transcribe should be called on the transcriber
                mock_transcriber.transcribe_audio.assert_called_once()

    @patch("blaze.managers.transcription_manager.TranscriptionManager.check_gpu_memory")
    def test_switch_from_dummy_to_working_backend(self, mock_check_gpu):
        """Test switching from failed backend (dummy) to working backend.

        This test simulates the real-world scenario where:
        1. App starts with unavailable backend (Liquid) - creates dummy transcriber
        2. User switches to available backend (Whisper) - should work without crash
        """
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        mock_check_gpu.return_value = (True, "GPU memory OK")

        mock_settings = Mock()
        # Start with liquid model (will fail), then switch to whisper
        call_count = [0]

        def side_effect_func(key, default=None):
            call_count[0] += 1
            # First batch (initialize with liquid): calls 1-4
            # After switch: calls 5+ (whisper)
            if call_count[0] <= 4:
                return {"model": "lfm2.5-audio-1.5b", "language": "auto"}.get(
                    key, default
                )
            else:
                return {"model": "whisper-base", "language": "auto"}.get(key, default)

        mock_settings.get.side_effect = side_effect_func

        # Make CoordinatorTranscriber fail (simulating missing dependencies)
        with patch(
            "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
        ) as mock_coordinator:
            mock_coordinator.side_effect = ImportError("liquid module not installed")

            with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
                # Create spec'd mock for proper type detection
                mock_whisper_instance = Mock(spec=WhisperTranscriber)
                mock_whisper_instance.is_model_loaded.return_value = True
                mock_whisper_instance.cleanup = Mock()
                mock_whisper.return_value = mock_whisper_instance

                # Step 1: Initialize with Liquid (will fail, creates dummy)
                manager = TranscriptionManager(mock_settings)
                result = manager.initialize()
                assert result is False, (
                    "Should fail to initialize with unavailable backend"
                )
                assert manager._get_transcriber_type() == "dummy", (
                    "Should have dummy transcriber"
                )

                # Step 2: Switch to Whisper (should succeed)
                success = manager._check_backend_change()
                assert success is True, "Should successfully switch to working backend"
                assert manager._get_transcriber_type() == "whisper", (
                    "Should have whisper transcriber"
                )
                assert manager.transcriber is mock_whisper_instance

                # Verify cleanup was called on dummy transcriber (if it has cleanup)
                # and Whisper transcriber was properly initialized


class TestTranscriberFactory:
    """Test TranscriberFactory for proper backend routing."""

    def test_factory_creates_whisper_transcriber_for_whisper_backend(self):
        """Factory should create WhisperTranscriber for whisper backend."""
        from blaze.managers.transcription_manager import TranscriberFactory

        with patch("blaze.transcriber.WhisperTranscriber") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            transcriber = TranscriberFactory.create_transcriber("whisper", Mock())

            mock_class.assert_called_once()
            assert transcriber is mock_instance

    def test_factory_creates_coordinator_transcriber_for_other_backends(self):
        """Factory should create CoordinatorTranscriber for non-whisper backends."""
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
