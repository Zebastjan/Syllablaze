"""Clipboard manager for Syllablaze.

Pure clipboard service with no UI dependencies. Uses ClipboardPersistenceService
for Wayland-compatible clipboard ownership.

Signals:
    transcription_copied(text): Emitted when transcription text is copied
    clipboard_error(error): Emitted when clipboard operation fails
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import subprocess
import logging

from .services.clipboard_persistence_service import ClipboardPersistenceService

logger = logging.getLogger(__name__)


class ClipboardManager(QObject):
    """Manages clipboard operations for transcribed text.

    This is a pure service with no UI dependencies. It delegates clipboard
    persistence to ClipboardPersistenceService and emits signals for success
    and error conditions. The orchestrator subscribes to these signals and
    handles notifications separately.

    Signals:
        transcription_copied(text): Emitted when text is copied to clipboard
        clipboard_error(error): Emitted when clipboard operation fails
    """

    transcription_copied = pyqtSignal(str)
    clipboard_error = pyqtSignal(str)

    def __init__(self, settings=None, persistence_service=None):
        """Initialize clipboard manager.

        Parameters:
        -----------
        settings : Settings, optional
            Application settings instance
        persistence_service : ClipboardPersistenceService, optional
            Existing persistence service instance. If not provided, one will be created.
        """
        super().__init__()
        self.settings = settings

        # Use provided persistence service or create one
        if persistence_service:
            self._persistence_service = persistence_service
        else:
            self._persistence_service = ClipboardPersistenceService(settings)

        # Wire persistence service signals through to our signals
        self._persistence_service.clipboard_set.connect(self.transcription_copied)
        self._persistence_service.clipboard_error.connect(self.clipboard_error)

        logger.info("ClipboardManager: Initialized (pure service, no UI deps)")

    @pyqtSlot(str)
    def copy_to_clipboard(self, text):
        """Copy transcribed text to clipboard.

        Delegates to ClipboardPersistenceService and emits signals for result.
        No UI operations - notifications are handled by the orchestrator via signals.

        Parameters:
        -----------
        text : str
            Transcribed text to copy

        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        if not text:
            logger.warning("ClipboardManager: Received empty text, skipping")
            return False

        # Delegate to persistence service
        # Signals will be emitted automatically via the connections above
        success = self._persistence_service.set_text(text)

        if success:
            logger.info(f"ClipboardManager: Copied transcription: {text[:50]}...")
        else:
            logger.error("ClipboardManager: Failed to copy to clipboard")

        return success

    def paste_text(self, text):
        """Copy text to clipboard for auto-paste functionality.

        Copies text to clipboard and optionally pastes to active window.

        Parameters:
        -----------
        text : str
            Text to copy
        """
        if not text:
            logger.warning("ClipboardManager: Received empty text for paste, skipping")
            return

        logger.info(f"ClipboardManager: Copying for paste: {text[:50]}...")

        # Copy to clipboard
        success = self._persistence_service.set_text(text)

        if success and self._should_paste_to_active_window():
            self._paste_to_active_window()

    def _paste_to_active_window(self):
        """Simulate Ctrl+V to paste to active window."""
        try:
            subprocess.run(["xdotool", "key", "ctrl+v"], check=True)
            logger.info("ClipboardManager: Pasted to active window")
        except Exception as e:
            logger.error(f"ClipboardManager: Failed to paste to active window: {e}")

    def _should_paste_to_active_window(self):
        """Check if should auto-paste to active window."""
        # TODO: Get this from settings when the feature is implemented
        return False

    def get_text(self):
        """Get text from clipboard.

        Returns:
        --------
        str
            Current clipboard text or empty string
        """
        return self._persistence_service.get_text()

    def clear(self):
        """Clear the clipboard.

        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        return self._persistence_service.clear()

    def shutdown(self):
        """Shutdown the clipboard manager gracefully."""
        logger.info("ClipboardManager: Shutting down")
        if self._persistence_service:
            self._persistence_service.shutdown()
