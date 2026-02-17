"""
Orchestration layer for Syllablaze.

This module defines the clean separation of concerns that was previously
tangled in the SyllablazeOrchestrator god-class in main.py.

Current state (Phase 1): Thin stubs that delegate to existing managers.
Future phases will gradually move logic here from main.py.
"""

from typing import Protocol, runtime_checkable
from PyQt6.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)


# === Protocol contracts (Step 7) ===

@runtime_checkable
class AudioBackend(Protocol):
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
    def get_volume(self) -> float: ...


@runtime_checkable
class TranscriptionBackend(Protocol):
    def transcribe(self, audio_data) -> str: ...
    def load_model(self, model_name: str, device: str, compute_type: str) -> None: ...


# === Sub-controllers ===

class RecordingController(QObject):
    """Owns the record → stop → transcribe → clipboard pipeline.

    Currently a thin wrapper — real logic lives in main.py's
    SyllablazeOrchestrator. Logic will migrate here in future phases.
    """

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    volume_update = pyqtSignal(float)
    transcription_complete = pyqtSignal(str)
    transcription_error = pyqtSignal(str)

    def __init__(self, audio_manager, transcription_manager, clipboard_manager,
                 ui_manager, settings, app_state):
        super().__init__()
        self.audio_manager = audio_manager
        self.transcription_manager = transcription_manager
        self.clipboard_manager = clipboard_manager
        self.ui_manager = ui_manager
        self.settings = settings
        self.app_state = app_state

        # Wire app_state signals to our signals for external subscribers
        if app_state:
            app_state.recording_started.connect(self.recording_started)
            app_state.recording_stopped.connect(self.recording_stopped)
            app_state.transcription_stopped.connect(self._on_transcription_stopped)

    def _on_transcription_stopped(self):
        """Relay transcription completion — used by popup mode."""
        # Emitted after handle_transcription_finished sets result
        # The actual text is not available here; popup mode only needs the signal
        self.transcription_complete.emit("")


class SettingsService(QObject):
    """Reactive wrapper around Settings — emits setting_changed(key, value).

    Replaces SettingsCoordinator where appropriate.
    Currently coexists with SettingsCoordinator during migration.
    """

    setting_changed = pyqtSignal(str, object)

    def __init__(self, settings):
        super().__init__()
        self._settings = settings

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings.set(key, value)
        self.setting_changed.emit(key, value)


class WindowManager(QObject):
    """Creates, shows, hides, and destroys all non-tray windows.

    Currently a thin wrapper around UIManager — window lifecycle
    methods will migrate here from main.py in future phases.
    """

    def __init__(self, ui_manager, settings_coordinator=None):
        super().__init__()
        self.ui_manager = ui_manager
        self.settings_coordinator = settings_coordinator

    def show_progress(self, settings, title="Voice Recording", stop_callback=None):
        """Create and show the progress window for a recording session."""
        progress_window = self.ui_manager.create_progress_window(settings, title)
        if progress_window:
            if self.settings_coordinator:
                self.settings_coordinator.set_progress_window(progress_window)
            if stop_callback:
                progress_window.stop_clicked.connect(stop_callback)
            progress_window.show()
            progress_window.raise_()
            progress_window.activateWindow()
        return progress_window

    def hide_progress(self, context=""):
        """Hide and clean up the progress window."""
        self.ui_manager.close_progress_window(context)

    def show_settings(self, settings_window):
        """Show the settings window."""
        if settings_window:
            settings_window.show()
            settings_window.raise_()
            settings_window.activateWindow()

    def hide_settings(self, settings_window):
        """Hide the settings window."""
        if settings_window:
            settings_window.hide()

    def close_all(self, settings_window):
        """Close all managed windows (called on shutdown)."""
        if settings_window:
            self.ui_manager.safely_close_window(settings_window, "settings")
        self.ui_manager.close_progress_window("shutdown")


class SyllablazeOrchestrator(QObject):
    """Top-level conductor — the ONLY class that UI talks to.

    Currently a thin delegation layer that wires together the existing
    manager classes. In future phases the tray class in main.py will
    shrink as logic migrates here.

    Public API:
        toggle_recording()
        update_settings(key, value)
        open_settings_window()
        shutdown()

    Signals:
        recording_started — recording has begun
        recording_stopped — recording has stopped
        transcription_ready(str) — transcription text available
        status_changed(str) — status message update
        error_occurred(str) — error message
    """

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_ready = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, audio_manager, transcription_manager, clipboard_manager,
                 ui_manager, settings, app_state, settings_coordinator=None):
        super().__init__()

        self.settings = settings
        self.app_state = app_state

        # Create sub-controllers
        self.recording_controller = RecordingController(
            audio_manager=audio_manager,
            transcription_manager=transcription_manager,
            clipboard_manager=clipboard_manager,
            ui_manager=ui_manager,
            settings=settings,
            app_state=app_state,
        )
        self.settings_service = SettingsService(settings)
        self.window_manager = WindowManager(
            ui_manager=ui_manager,
            settings_coordinator=settings_coordinator,
        )

        # Wire sub-controller signals to our public API signals
        self.recording_controller.recording_started.connect(self.recording_started)
        self.recording_controller.recording_stopped.connect(self.recording_stopped)
        self.recording_controller.transcription_complete.connect(self.transcription_ready)
        self.recording_controller.transcription_error.connect(self.error_occurred)

    def toggle_recording(self):
        """Delegate to the tray orchestrator (transition period)."""
        # During migration, the actual toggle logic still lives in main.py.
        # This will be filled in when RecordingController takes over.
        pass

    def update_settings(self, key, value):
        """Update a setting reactively."""
        self.settings_service.set(key, value)

    def open_settings_window(self):
        """Signal intent to open settings — tray handles the actual window."""
        pass

    def shutdown(self):
        """Signal shutdown intent — tray handles actual cleanup."""
        pass
