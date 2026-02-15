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

    # Window visibility signals (will be added in Phase 4)
    # recording_dialog_visibility_changed = pyqtSignal(bool)
    # progress_window_visibility_changed = pyqtSignal(bool)

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
        }
