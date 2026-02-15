"""
Application State Manager for Syllablaze

Centralizes all application state in a single source of truth.
All components query this state instead of maintaining their own copies.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ApplicationState(QObject):
    """Single source of truth for all application state.

    All state changes emit signals so components can react accordingly.
    Components should NOT modify state directly - they should call methods
    on this class which will update state and emit appropriate signals.
    """

    # Recording state signals
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_state_changed = pyqtSignal(bool)  # is_recording

    # Transcription state signals
    transcription_started = pyqtSignal()
    transcription_stopped = pyqtSignal()
    transcription_state_changed = pyqtSignal(bool)  # is_transcribing

    # Window visibility signals
    recording_dialog_visibility_changed = pyqtSignal(bool, str)  # visible, source
    progress_window_visibility_changed = pyqtSignal(bool)  # visible

    def __init__(self, settings):
        """Initialize application state.

        Parameters:
        -----------
        settings : Settings
            Application settings instance
        """
        super().__init__()
        self.settings = settings

        # Recording state
        self._is_recording = False

        # Transcription state
        self._is_transcribing = False

        # Window visibility state
        # Initialize from settings
        self._recording_dialog_visible = settings.get("show_recording_dialog", True)
        self._progress_window_visible = settings.get("show_progress_window", True)

        logger.info("ApplicationState initialized")

    # === Recording State ===

    def is_recording(self):
        """Get current recording state.

        Returns:
        --------
        bool
            True if currently recording
        """
        return self._is_recording

    def start_recording(self):
        """Start recording - updates state and emits signals.

        Returns:
        --------
        bool
            True if state changed, False if already recording
        """
        if self._is_recording:
            logger.warning("start_recording() called but already recording")
            return False

        logger.info("ApplicationState: Starting recording")
        self._is_recording = True
        self.recording_state_changed.emit(True)
        self.recording_started.emit()
        return True

    def stop_recording(self):
        """Stop recording - updates state and emits signals.

        Returns:
        --------
        bool
            True if state changed, False if not recording
        """
        if not self._is_recording:
            logger.warning("stop_recording() called but not recording")
            return False

        logger.info("ApplicationState: Stopping recording")
        self._is_recording = False
        self.recording_state_changed.emit(False)
        self.recording_stopped.emit()
        return True

    # === Transcription State ===

    def is_transcribing(self):
        """Get current transcription state.

        Returns:
        --------
        bool
            True if currently transcribing
        """
        return self._is_transcribing

    def start_transcription(self):
        """Start transcription - updates state and emits signals.

        Returns:
        --------
        bool
            True if state changed, False if already transcribing
        """
        if self._is_transcribing:
            logger.warning("start_transcription() called but already transcribing")
            return False

        logger.info("ApplicationState: Starting transcription")
        self._is_transcribing = True
        self.transcription_state_changed.emit(True)
        self.transcription_started.emit()
        return True

    def stop_transcription(self):
        """Stop transcription - updates state and emits signals.

        Returns:
        --------
        bool
            True if state changed, False if not transcribing
        """
        if not self._is_transcribing:
            logger.warning("stop_transcription() called but not transcribing")
            return False

        logger.info("ApplicationState: Stopping transcription")
        self._is_transcribing = False
        self.transcription_state_changed.emit(False)
        self.transcription_stopped.emit()
        return True

    # === Window Visibility State ===

    def is_recording_dialog_visible(self):
        """Get recording dialog visibility state.

        Returns:
        --------
        bool
            True if recording dialog should be visible
        """
        return self._recording_dialog_visible

    def set_recording_dialog_visible(self, visible, source="unknown"):
        """Set recording dialog visibility state.

        This is the single source of truth for dialog visibility.
        Updates both state and settings, then emits signal.

        Parameters:
        -----------
        visible : bool
            True to show dialog, False to hide
        source : str
            Source of the visibility change (for debugging)
        """
        if self._recording_dialog_visible == visible:
            logger.debug(
                f"Recording dialog visibility unchanged ({visible}) from {source}"
            )
            return False

        logger.info(
            f"ApplicationState: Recording dialog visibility {self._recording_dialog_visible} -> {visible} (source: {source})"
        )
        self._recording_dialog_visible = visible

        # Update settings to persist the change
        self.settings.set("show_recording_dialog", visible)

        # Emit signal so UI components can react
        self.recording_dialog_visibility_changed.emit(visible, source)
        return True

    def is_progress_window_visible(self):
        """Get progress window visibility state.

        Returns:
        --------
        bool
            True if progress window should be visible
        """
        return self._progress_window_visible

    def set_progress_window_visible(self, visible):
        """Set progress window visibility state.

        Parameters:
        -----------
        visible : bool
            True to show window, False to hide
        """
        if self._progress_window_visible == visible:
            return False

        logger.info(
            f"ApplicationState: Progress window visibility {self._progress_window_visible} -> {visible}"
        )
        self._progress_window_visible = visible

        # Update settings to persist the change
        self.settings.set("show_progress_window", visible)

        # Emit signal so UI components can react
        self.progress_window_visibility_changed.emit(visible)
        return True

    # === State Query Methods ===

    def get_state_summary(self):
        """Get a summary of current state for debugging.

        Returns:
        --------
        dict
            Dictionary containing current state values
        """
        return {
            'recording': self._is_recording,
            'transcribing': self._is_transcribing,
            'recording_dialog_visible': self._recording_dialog_visible,
            'progress_window_visible': self._progress_window_visible,
        }
