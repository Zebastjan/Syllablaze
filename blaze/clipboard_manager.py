from PyQt6.QtCore import QObject, pyqtSlot, QMimeData, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QWidget
import subprocess
import logging

logger = logging.getLogger(__name__)


class ClipboardManager(QObject):
    """Manages clipboard operations for transcribed text.

    Uses a persistent hidden window on Wayland to ensure clipboard content
    survives after transient windows (like the recording dialog) close.
    On Wayland, clipboard ownership is tied to the window that set it.
    If that window closes, the clipboard may be cleared by the compositor.
    """

    def __init__(self, settings, ui_manager):
        """Initialize clipboard manager.

        Parameters:
        -----------
        settings : Settings
            Application settings instance
        ui_manager : UIManager
            UI manager for showing notifications
        """
        super().__init__()
        self.settings = settings
        self.ui_manager = ui_manager
        self.clipboard = QApplication.clipboard()

        # Create a persistent widget to own the clipboard on Wayland
        # This window is shown briefly during each clipboard operation to anchor ownership
        self._clipboard_owner = QWidget()
        self._clipboard_owner.setWindowTitle("Syllablaze Clipboard Owner")
        self._clipboard_owner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._clipboard_owner.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        )
        self._clipboard_owner.resize(1, 1)  # Minimal size

        # Initially hide the window
        self._clipboard_owner.hide()
        self._current_mime_data = None

        logger.info("ClipboardManager: Initialized with Wayland-compatible clipboard owner")

    def paste_text(self, text):
        """Copy text to clipboard for auto-paste functionality."""
        if not text:
            logger.warning("Received empty text, skipping clipboard operation")
            return

        logger.info(f"Copying text to clipboard: {text[:50]}...")

        # WAYLAND FIX: Show clipboard owner during operation
        logger.debug("Showing clipboard owner window for Wayland ownership")
        self._clipboard_owner.show()

        # Use mime data with persistent ownership
        mime_data = QMimeData()
        mime_data.setText(text)
        self._current_mime_data = mime_data
        self.clipboard.setMimeData(mime_data, mode=self.clipboard.Mode.Clipboard)

        # Keep visible during paste operation, hide after
        QTimer.singleShot(500, self._hide_clipboard_owner)

        # If set to paste to active window, simulate Ctrl+V
        if self.should_paste_to_active_window():
            self.paste_to_active_window()

    def paste_to_active_window(self):
        try:
            # Use xdotool to simulate Ctrl+V
            subprocess.run(["xdotool", "key", "ctrl+v"], check=True)
        except Exception as e:
            logger.error(f"Failed to paste to active window: {e}")

    def should_paste_to_active_window(self):
        # TODO: Get this from settings
        return False

    @pyqtSlot(str)
    def copy_to_clipboard(self, text, tray_icon=None, normal_icon=None):
        """Copy transcribed text to clipboard and show notification.

        WAYLAND FIX: Shows clipboard owner window during operation to maintain ownership.

        Parameters:
        -----------
        text : str
            Transcribed text to copy
        tray_icon : QSystemTrayIcon, optional
            Tray icon for tooltip update
        normal_icon : QIcon, optional
            Icon to use for notification
        """
        if not text:
            logger.warning("Received empty text, skipping clipboard operation")
            return

        try:
            # CRITICAL WAYLAND FIX: Show clipboard owner window BEFORE setting clipboard
            # This ensures a visible window owns the clipboard when other windows (like applet) hide
            logger.debug("Showing clipboard owner window for Wayland ownership")
            self._clipboard_owner.show()

            # Create mime data with the text
            mime_data = QMimeData()
            mime_data.setText(text)
            self._current_mime_data = mime_data

            # Set the clipboard from our persistent owner window
            # The window being visible ensures Wayland grants and maintains ownership
            self.clipboard.setMimeData(mime_data, mode=self.clipboard.Mode.Clipboard)

            logger.info(f"Copied transcription to clipboard: {text[:50]}...")

            # Keep clipboard owner visible for 500ms to ensure ownership is fully established
            # Then hide it after clipboard is secured
            QTimer.singleShot(500, self._hide_clipboard_owner)

            # Truncate text for notification if too long
            display_text = text
            if len(text) > 100:
                display_text = text[:100] + "..."

            # Show notification with the transcribed text
            self.ui_manager.show_notification(
                tray_icon, "Transcription Complete", display_text, normal_icon
            )

            logger.info("Clipboard copy and notification complete")

        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            # Hide clipboard owner even on error
            self._clipboard_owner.hide()
            # Show error notification
            if self.ui_manager and tray_icon:
                self.ui_manager.show_notification(
                    tray_icon,
                    "Clipboard Error",
                    f"Failed to copy transcription: {str(e)}",
                    normal_icon,
                )

    def _hide_clipboard_owner(self):
        """Hide clipboard owner window after clipboard operation completes."""
        self._clipboard_owner.hide()
        logger.debug("Clipboard owner window hidden after operation")
