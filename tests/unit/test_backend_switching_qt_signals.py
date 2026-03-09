"""
End-to-End Tests for Backend Switching with Qt Signal/Slot Context

These tests simulate the full UI flow for backend switching, including
the Qt signal/slot mechanism that was causing crashes in the real app.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# We need Qt for these tests
pytest.importorskip("PyQt6")

from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication, QTimer
from PyQt6.QtTest import QSignalSpy


class MockSettingsBridge(QObject):
    """Mock settings bridge that mimics the real SettingsBridge."""

    activeModelChanged = pyqtSignal(str)
    settingChanged = pyqtSignal(str, object)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def setActiveModel(self, model_name):
        """Set active model and emit signal (just like real SettingsBridge)."""
        self.settings.set("model", model_name)
        self.settingChanged.emit("model", model_name)
        # Emit the signal that triggers hard reset
        self.activeModelChanged.emit(model_name)


class MockOrchestrator(QObject):
    """Mock orchestrator that handles model change signals."""

    def __init__(self, transcription_manager, app_state, parent=None):
        super().__init__(parent)
        self.transcription_manager = transcription_manager
        self.app_state = app_state
        self.notification_shown = False
        self.notification_title = None
        self.notification_message = None
        self._deferred_calls = []

    def _handle_model_change_hard_reset(self, model_name):
        """Handle model change - simulates real implementation."""
        from PyQt6.QtCore import QTimer

        # Stop any ongoing transcription
        if self.app_state.is_transcribing():
            self.app_state.stop_transcription()

        # Defer reinitialization to next event loop iteration
        # This prevents Qt lifecycle issues
        QTimer.singleShot(0, lambda: self._deferred_backend_reinit(model_name))

    def _deferred_backend_reinit(self, model_name):
        """Deferred reinitialization - runs in next event loop iteration."""
        try:
            success = self.transcription_manager._check_backend_change()

            if success:
                self.notification_title = "Model Changed"
                self.notification_message = f"Switched to {model_name}"
            else:
                transcriber_type = self.transcription_manager._get_transcriber_type()
                if transcriber_type == "dummy":
                    self.notification_title = "Model Not Available"
                    self.notification_message = "Backend not available"
                else:
                    self.notification_title = "Model Change Failed"
                    self.notification_message = f"Could not switch to {model_name}"

            self.notification_shown = True

        except Exception as e:
            self.notification_title = "Model Change Error"
            self.notification_message = str(e)
            self.notification_shown = True


class TestBackendSwitchingQtSignals:
    """Test backend switching through Qt signal/slot mechanism."""

    def test_model_change_signal_triggers_reinit(self, qtbot):
        """Test that model change signal properly triggers backend reinitialization."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        # Create QApplication if not exists
        app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        with patch.object(
            TranscriptionManager, "check_gpu_memory", return_value=(True, "OK")
        ):
            # Setup mock settings
            mock_settings = Mock()
            mock_settings.get.side_effect = lambda key, default=None: {
                "model": "whisper-base",
                "language": "auto",
            }.get(key, default)

            with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
                # Create spec'd mock
                mock_whisper_instance = Mock(spec=WhisperTranscriber)
                mock_whisper_instance.is_model_loaded.return_value = True
                mock_whisper_instance.cleanup = Mock()
                mock_whisper.return_value = mock_whisper_instance

                # Create transcription manager
                manager = TranscriptionManager(mock_settings)
                manager.initialize()

                # Create mock app state
                app_state = Mock()
                app_state.is_transcribing.return_value = False
                app_state.stop_transcription = Mock()

                # Create orchestrator
                orchestrator = MockOrchestrator(manager, app_state)

                # Create settings bridge
                settings_bridge = MockSettingsBridge(mock_settings)
                settings_bridge.activeModelChanged.connect(
                    orchestrator._handle_model_change_hard_reset
                )

                # Emit the signal (this simulates user selecting new model in UI)
                with qtbot.waitSignal(
                    settings_bridge.activeModelChanged, timeout=1000
                ) as blocker:
                    settings_bridge.setActiveModel("whisper-large-v3")
                    blocker.connect(
                        orchestrator._deferred_backend_reinit
                    )  # Wait for deferred call too

                # Process events to allow deferred reinitialization
                qtbot.wait(100)

                # Verify notification was shown
                assert orchestrator.notification_shown is True
                assert orchestrator.notification_title == "Model Changed"

    def test_switch_from_dummy_to_working_via_signal(self, qtbot):
        """Test switching from dummy transcriber to working one via Qt signals."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        # Create QApplication if not exists
        app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        with patch.object(
            TranscriptionManager, "check_gpu_memory", return_value=(True, "OK")
        ):
            mock_settings = Mock()
            # Start with liquid (will fail), then switch to whisper
            call_count = [0]

            def side_effect_func(key, default=None):
                call_count[0] += 1
                if call_count[0] <= 4:
                    return {"model": "lfm2.5-audio-1.5b", "language": "auto"}.get(
                        key, default
                    )
                else:
                    return {"model": "whisper-base", "language": "auto"}.get(
                        key, default
                    )

            mock_settings.get.side_effect = side_effect_func

            # Make CoordinatorTranscriber fail
            with patch(
                "blaze.managers.coordinator_transcriber.CoordinatorTranscriber"
            ) as mock_coordinator:
                mock_coordinator.side_effect = ImportError(
                    "liquid module not installed"
                )

                with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
                    mock_whisper_instance = Mock(spec=WhisperTranscriber)
                    mock_whisper_instance.is_model_loaded.return_value = True
                    mock_whisper_instance.cleanup = Mock()
                    mock_whisper.return_value = mock_whisper_instance

                    # Initialize with Liquid (will fail, creates dummy)
                    manager = TranscriptionManager(mock_settings)
                    result = manager.initialize()
                    assert result is False
                    assert manager._get_transcriber_type() == "dummy"

                    # Create mock app state
                    app_state = Mock()
                    app_state.is_transcribing.return_value = False

                    # Create orchestrator
                    orchestrator = MockOrchestrator(manager, app_state)

                    # Create settings bridge
                    settings_bridge = MockSettingsBridge(mock_settings)
                    settings_bridge.activeModelChanged.connect(
                        orchestrator._handle_model_change_hard_reset
                    )

                    # Emit signal to switch to Whisper
                    # Reset call count for settings.get calls during reinit
                    call_count[0] = 0

                    with qtbot.waitSignal(
                        settings_bridge.activeModelChanged, timeout=1000
                    ):
                        settings_bridge.setActiveModel("whisper-base")

                    # Process events
                    qtbot.wait(100)

                    # Verify successful switch
                    assert orchestrator.notification_shown is True
                    assert orchestrator.notification_title == "Model Changed"
                    assert manager._get_transcriber_type() == "whisper"

    def test_multiple_rapid_backend_switches(self, qtbot):
        """Test that rapid backend switches don't cause crashes or leaks."""
        from blaze.managers.transcription_manager import TranscriptionManager
        from blaze.transcriber import WhisperTranscriber

        # Create QApplication if not exists
        app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        with patch.object(
            TranscriptionManager, "check_gpu_memory", return_value=(True, "OK")
        ):
            mock_settings = Mock()
            mock_settings.get.side_effect = lambda key, default=None: {
                "model": "whisper-base",
                "language": "auto",
            }.get(key, default)

            with patch("blaze.transcriber.WhisperTranscriber") as mock_whisper:
                mock_whisper_instance = Mock(spec=WhisperTranscriber)
                mock_whisper_instance.is_model_loaded.return_value = True
                mock_whisper_instance.cleanup = Mock()
                mock_whisper.return_value = mock_whisper_instance

                manager = TranscriptionManager(mock_settings)
                manager.initialize()

                app_state = Mock()
                app_state.is_transcribing.return_value = False

                orchestrator = MockOrchestrator(manager, app_state)

                settings_bridge = MockSettingsBridge(mock_settings)
                settings_bridge.activeModelChanged.connect(
                    orchestrator._handle_model_change_hard_reset
                )

                # Perform multiple rapid switches
                models = ["whisper-tiny", "whisper-base", "whisper-small"]
                for model in models:
                    with qtbot.waitSignal(
                        settings_bridge.activeModelChanged, timeout=1000
                    ):
                        settings_bridge.setActiveModel(model)

                    qtbot.wait(100)

                # All switches should complete without crash
                assert manager._get_transcriber_type() == "whisper"


class TestErrorRecoveryQtSignals:
    """Test error recovery scenarios with Qt signal/slot context."""

    def test_reinitialization_failure_recovery(self, qtbot):
        """Test that app recovers gracefully when reinitialization fails."""
        from blaze.managers.transcription_manager import TranscriptionManager

        app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "model": "granite-speech-3.3-2b",  # Will fail
            "language": "auto",
        }.get(key, default)

        # Make initialization fail
        with patch.object(
            TranscriptionManager, "initialize", return_value=False
        ) as mock_init:
            manager = TranscriptionManager(mock_settings)
            manager.initialize()

            app_state = Mock()
            orchestrator = MockOrchestrator(manager, app_state)

            settings_bridge = MockSettingsBridge(mock_settings)
            settings_bridge.activeModelChanged.connect(
                orchestrator._handle_model_change_hard_reset
            )

            # Emit signal - should not crash even though init will fail
            with qtbot.waitSignal(settings_bridge.activeModelChanged, timeout=1000):
                settings_bridge.setActiveModel("granite-speech-3.3-2b")

            qtbot.wait(100)

            # Should show error notification, not crash
            assert orchestrator.notification_shown is True
            assert (
                "Error" in orchestrator.notification_title
                or "Failed" in orchestrator.notification_title
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
