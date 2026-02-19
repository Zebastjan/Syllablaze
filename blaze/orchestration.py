"""
Orchestration layer for Syllablaze.

This module defines the clean separation of concerns that was previously
tangled in the SyllablazeOrchestrator god-class in main.py.

Current state (Phase 2): RecordingController now owns the full pipeline.
- Recording start/stop logic migrated from main.py
- Transcription pipeline orchestration
- Clipboard operations with proper timing
"""

from typing import Protocol, runtime_checkable, Optional
from PyQt6.QtCore import QObject, pyqtSignal
import logging
import numpy as np

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

    Handles the complete recording lifecycle:
    1. Check readiness and acquire lock
    2. Start recording (create progress window, update state)
    3. Stop recording (process audio data)
    4. Transcribe audio
    5. Copy to clipboard with proper timing for Wayland

    Emits signals at each phase for UI updates.
    """

    # Recording lifecycle signals
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    volume_update = pyqtSignal(float)

    # Transcription signals
    transcription_started = pyqtSignal()
    transcription_progress = pyqtSignal(str)  # status message
    transcription_progress_percent = pyqtSignal(int)  # 0-100
    transcription_complete = pyqtSignal(str)  # transcribed text
    transcription_error = pyqtSignal(str)  # error message

    # Error signals
    recording_error = pyqtSignal(str)
    readiness_error = pyqtSignal(str)  # Emitted when not ready to record

    # UI request signals
    progress_window_requested = pyqtSignal()  # Request to show progress window
    progress_window_close_requested = pyqtSignal(str)  # Request to close with context

    def __init__(
        self,
        audio_manager,
        transcription_manager,
        clipboard_manager,
        notification_service,
        settings,
        app_state,
    ):
        super().__init__()
        self.audio_manager = audio_manager
        self.transcription_manager = transcription_manager
        self.clipboard_manager = clipboard_manager
        self.notification_service = notification_service
        self.settings = settings
        self.app_state = app_state

        # Wire up internal signals
        self._setup_signal_connections()

        logger.info("RecordingController: Initialized")

    def _setup_signal_connections(self):
        """Setup internal signal connections."""
        # Wire audio manager signals through
        if self.audio_manager:
            self.audio_manager.volume_changing.connect(self.volume_update)
            self.audio_manager.recording_completed.connect(self._on_recording_completed)
            self.audio_manager.recording_failed.connect(self._on_recording_failed)

        # Wire transcription manager signals through
        if self.transcription_manager:
            self.transcription_manager.transcription_progress.connect(
                self.transcription_progress
            )
            self.transcription_manager.transcription_progress_percent.connect(
                self.transcription_progress_percent
            )
            self.transcription_manager.transcription_finished.connect(
                self._on_transcription_finished
            )
            self.transcription_manager.transcription_error.connect(
                self._on_transcription_error
            )

        # Wire clipboard manager signals
        if self.clipboard_manager:
            self.clipboard_manager.transcription_copied.connect(self._on_clipboard_set)
            self.clipboard_manager.clipboard_error.connect(self._on_clipboard_error)

    def toggle_recording(self) -> bool:
        """Toggle recording state with full pipeline management.

        This is the main entry point for starting/stopping recording.
        Handles:
        - Lock acquisition
        - Readiness checks
        - State transitions
        - Error handling

        Returns:
            bool: True if toggle was handled, False if lock not acquired
        """
        # Acquire lock to prevent concurrent operations
        if not self.audio_manager or not self.audio_manager.acquire_recording_lock():
            logger.info("Recording toggle already in progress, ignoring request")
            return False

        try:
            is_recording = self.app_state.is_recording()
            logger.info(
                f"Toggle recording: {'recording' if is_recording else 'not recording'}"
            )

            if is_recording:
                return self._stop_recording()
            else:
                return self._start_recording()
        finally:
            # Always release the lock
            self.audio_manager.release_recording_lock()

    def _start_recording(self) -> bool:
        """Start the recording flow.

        Returns:
            bool: True if started successfully, False otherwise
        """
        # Phase 1: Check readiness
        ready, error_msg = self._check_readiness()
        if not ready:
            logger.warning(f"Not ready to record: {error_msg}")
            self.readiness_error.emit(error_msg)
            return False

        # Phase 2: Request progress window
        self.progress_window_requested.emit()

        # Phase 3: Start recording
        try:
            result = self.audio_manager.start_recording()
            if result:
                # Phase 4: Update state (this emits recording_started)
                self.app_state.start_recording()
                self.recording_started.emit()
                logger.info("Recording started successfully")
                return True
            else:
                logger.error("Failed to start recording")
                self.recording_error.emit("Failed to start recording")
                return False
        except Exception as e:
            logger.error(f"Exception starting recording: {e}")
            self.recording_error.emit(str(e))
            return False

    def _stop_recording(self) -> bool:
        """Stop recording and start transcription.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        # Phase 1: Mark as transcribing
        self.app_state.start_transcription()
        self.transcription_started.emit()

        # Phase 2: Stop the recording
        try:
            result = self.audio_manager.stop_recording()
            if result:
                logger.info("Recording stopped successfully")
                # State will be updated when audio data arrives via signal
                return True
            else:
                logger.error("Failed to stop recording")
                self._handle_recording_stop_failure()
                return False
        except Exception as e:
            logger.error(f"Exception stopping recording: {e}")
            self._handle_recording_stop_failure(str(e))
            return False

    def _check_readiness(self) -> tuple[bool, str]:
        """Check if ready to start recording.

        Returns:
            tuple: (is_ready, error_message)
        """
        if not self.audio_manager:
            return False, "Audio manager not initialized"

        return self.audio_manager.is_ready_to_record(
            self.transcription_manager, self.app_state
        )

    def _handle_recording_stop_failure(self, error: Optional[str] = None):
        """Handle recording stop failure."""
        msg = error or "Failed to stop recording"
        logger.error(f"Recording stop failed: {msg}")
        self.recording_error.emit(msg)
        self.app_state.stop_recording()
        self.progress_window_close_requested.emit("after recording error")

    def _on_recording_completed(self, audio_data: np.ndarray):
        """Handle completed recording audio data.

        Called when audio data is ready after stopping recording.
        Starts the transcription process.
        """
        logger.info(f"Recording completed, audio shape: {audio_data.shape}")

        # Update state
        self.app_state.stop_recording()
        self.recording_stopped.emit()

        # Start transcription
        self._start_transcription(audio_data)

    def _on_recording_failed(self, error: str):
        """Handle recording failure."""
        logger.error(f"Recording failed: {error}")
        self.recording_error.emit(error)
        self.app_state.stop_recording()
        self.progress_window_close_requested.emit("after recording error")

    def _start_transcription(self, audio_data: np.ndarray):
        """Start transcription of audio data."""
        if not self.transcription_manager:
            self.transcription_error.emit("Transcription manager not initialized")
            return

        try:
            # Normalize audio data
            normalized_data = self._normalize_audio(audio_data)

            # Check model is loaded
            if (
                not hasattr(self.transcription_manager.transcriber, "model")
                or not self.transcription_manager.transcriber.model
            ):
                raise RuntimeError("Whisper model not loaded")

            # Start transcription
            logger.info("Starting transcription...")
            self.transcription_manager.transcribe_audio(normalized_data)

        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            self.transcription_error.emit(str(e))
            self.app_state.stop_transcription()
            self.progress_window_close_requested.emit("after transcription error")

    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio data for transcription."""
        # Convert to float32 and normalize
        audio_float = audio_data.astype(np.float32)

        # Normalize to [-1, 1] range
        if audio_float.max() > 0:
            audio_float = audio_float / 32768.0

        return audio_float

    def _on_transcription_finished(self, text: str):
        """Handle completed transcription.

        CRITICAL: Sets clipboard BEFORE stopping transcription state.
        On Wayland, clipboard ownership is tied to window focus.
        We must set clipboard before any windows close.
        """
        logger.info(f"Transcription finished: {text[:50]}...")

        if text:
            # CRITICAL: Set clipboard BEFORE stopping transcription state
            # This ensures clipboard ownership is established before any UI changes
            self.clipboard_manager.copy_to_clipboard(text)

            # Emit signal for UI updates (tooltip, etc.)
            self.transcription_complete.emit(text)
        else:
            logger.warning("Transcription returned empty text")
            self.transcription_complete.emit("")

        # Now safe to stop transcription state
        # This may trigger dialog close in popup mode
        self.app_state.stop_transcription()

        # Request progress window close
        self.progress_window_close_requested.emit("after transcription")

    def _on_transcription_error(self, error: str):
        """Handle transcription error."""
        logger.error(f"Transcription error: {error}")
        self.transcription_error.emit(error)
        self.app_state.stop_transcription()
        self.progress_window_close_requested.emit("after transcription error")

    def _on_clipboard_set(self, text: str):
        """Handle successful clipboard set."""
        logger.info("Clipboard set successfully")
        # Emit notification via notification service
        if self.notification_service:
            self.notification_service.notify_transcription_complete(text)

    def _on_clipboard_error(self, error: str):
        """Handle clipboard error."""
        logger.error(f"Clipboard error: {error}")
        if self.notification_service:
            self.notification_service.notify_error("Clipboard Error", error)


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

    def __init__(
        self,
        audio_manager,
        transcription_manager,
        clipboard_manager,
        notification_service,
        settings,
        app_state,
        settings_coordinator=None,
    ):
        super().__init__()

        self.settings = settings
        self.app_state = app_state

        # Create sub-controllers
        self.recording_controller = RecordingController(
            audio_manager=audio_manager,
            transcription_manager=transcription_manager,
            clipboard_manager=clipboard_manager,
            notification_service=notification_service,
            settings=settings,
            app_state=app_state,
        )
        self.settings_service = SettingsService(settings)
        self.window_manager = WindowManager(
            ui_manager=None,  # Will be set later
            settings_coordinator=settings_coordinator,
        )

        # Wire sub-controller signals to our public API signals
        self.recording_controller.recording_started.connect(self.recording_started)
        self.recording_controller.recording_stopped.connect(self.recording_stopped)
        self.recording_controller.transcription_complete.connect(
            self.transcription_ready
        )
        self.recording_controller.transcription_error.connect(self.error_occurred)

    def toggle_recording(self):
        """Toggle recording state."""
        return self.recording_controller.toggle_recording()

    def update_settings(self, key, value):
        """Update a setting reactively."""
        self.settings_service.set(key, value)

    def open_settings_window(self):
        """Signal intent to open settings — tray handles the actual window."""
        pass

    def shutdown(self):
        """Signal shutdown intent — tray handles actual cleanup."""
        pass
