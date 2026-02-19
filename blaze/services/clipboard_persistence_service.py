"""Clipboard persistence service for Wayland compatibility.

On Wayland, clipboard ownership is tied to the window that set it. If that window
closes, the clipboard may be cleared by the compositor. This service provides a
dedicated, long-running hidden window that maintains clipboard ownership.

The service stays alive throughout the application lifecycle and handles:
- Clipboard setting with proper Wayland ownership
- Clipboard persistence across window lifecycle changes
- MIME data management for rich clipboard content
"""

from PyQt6.QtCore import QObject, pyqtSignal, QMimeData, Qt
from PyQt6.QtWidgets import QApplication, QWidget
import logging

logger = logging.getLogger(__name__)


class ClipboardPersistenceService(QObject):
    """Dedicated service for clipboard persistence on Wayland.

    This service owns a persistent hidden window that maintains clipboard
    ownership throughout the application lifecycle. Unlike the old approach
    of showing/hiding a temporary window, this window stays alive and
    visible (at 1x1 pixel size) to maintain ownership.

    Signals:
        clipboard_set(text): Emitted when text is successfully set to clipboard
        clipboard_error(error): Emitted when clipboard operation fails
    """

    clipboard_set = pyqtSignal(str)
    clipboard_error = pyqtSignal(str)

    def __init__(self, settings=None):
        """Initialize the clipboard persistence service.

        Creates a persistent hidden window that will own the clipboard
        throughout the application lifecycle.

        Parameters:
        -----------
        settings : Settings, optional
            Application settings instance (for future use)
        """
        super().__init__()
        self.settings = settings
        self.clipboard = QApplication.clipboard()
        self._current_mime_data = None

        # Create a persistent owner window that STAYS visible
        # This ensures Wayland maintains clipboard ownership
        self._owner_window = QWidget()
        self._owner_window.setWindowTitle("Syllablaze Clipboard Persistence")
        self._owner_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._owner_window.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnBottomHint  # Keep it out of the way
        )

        # 1x1 pixel - effectively invisible but "visible" to Wayland
        self._owner_window.resize(1, 1)

        # Position off-screen
        self._owner_window.move(-100, -100)

        # Show and keep it shown - this is critical for Wayland ownership
        self._owner_window.show()

        logger.info(
            "ClipboardPersistenceService: Initialized with persistent owner window"
        )

    def set_text(self, text):
        """Set text to clipboard with persistent ownership.

        The owner window is already visible, so clipboard ownership
        is immediately established and maintained.

        Parameters:
        -----------
        text : str
            Text to copy to clipboard

        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        if not text:
            logger.warning("ClipboardPersistenceService: Received empty text, skipping")
            return False

        try:
            # Create MIME data with the text
            mime_data = QMimeData()
            mime_data.setText(text)
            self._current_mime_data = mime_data

            # Set clipboard - window is already visible so ownership is immediate
            self.clipboard.setMimeData(mime_data, mode=self.clipboard.Mode.Clipboard)

            logger.info(
                f"ClipboardPersistenceService: Copied text to clipboard: {text[:50]}..."
            )

            # Emit success signal
            self.clipboard_set.emit(text)

            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"ClipboardPersistenceService: Failed to copy to clipboard: {error_msg}"
            )
            self.clipboard_error.emit(error_msg)
            return False

    def get_text(self):
        """Get text from clipboard.

        Returns:
        --------
        str
            Current clipboard text or empty string
        """
        return self.clipboard.text()

    def clear(self):
        """Clear the clipboard.

        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        try:
            mime_data = QMimeData()
            self.clipboard.setMimeData(mime_data, mode=self.clipboard.Mode.Clipboard)
            self._current_mime_data = None
            logger.info("ClipboardPersistenceService: Clipboard cleared")
            return True
        except Exception as e:
            logger.error(f"ClipboardPersistenceService: Failed to clear clipboard: {e}")
            return False

    def shutdown(self):
        """Shutdown the service gracefully.

        Called during application shutdown to clean up resources.
        """
        logger.info("ClipboardPersistenceService: Shutting down")
        if self._owner_window:
            self._owner_window.hide()
            self._owner_window.deleteLater()
            self._owner_window = None
