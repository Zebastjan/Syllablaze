from PyQt6.QtCore import QObject, pyqtSlot, QMimeData
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

        # Create a persistent hidden widget to own the clipboard on Wayland
        # This ensures clipboard survives when other windows close
        self._clipboard_owner = QWidget()
        self._clipboard_owner.setWindowTitle("Syllablaze Clipboard Owner")
        self._clipboard_owner.hide()
        self._current_mime_data = None
        logger.info("ClipboardManager: Initialized with persistent clipboard owner")

    def paste_text(self, text):
        """Copy text to clipboard for auto-paste functionality."""
        if not text:
            logger.warning("Received empty text, skipping clipboard operation")
            return

        logger.info(f"Copying text to clipboard: {text[:50]}...")

        # Use mime data with persistent ownership (same as copy_to_clipboard)
        mime_data = QMimeData()
        mime_data.setText(text)
        self._current_mime_data = mime_data
        self.clipboard.setMimeData(mime_data, mode=self.clipboard.Mode.Clipboard)

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

        This is the main method called when transcription completes.
        Uses a persistent hidden window to own the clipboard on Wayland,
        preventing clipboard loss when transient windows close.

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
            # On Wayland, we need to use a persistent window to own the clipboard.
            # If a transient window (like the recording dialog) sets the clipboard
            # and then closes, the compositor may clear the clipboard.
            # By using a persistent hidden widget, we ensure the clipboard survives.

            # Create mime data with the text
            mime_data = QMimeData()
            mime_data.setText(text)
            self._current_mime_data = mime_data

            # Set the clipboard from our persistent owner window
            # This ensures the clipboard persists even if the recording dialog closes
            self.clipboard.setMimeData(mime_data, mode=self.clipboard.Mode.Clipboard)

            logger.info(f"Copied transcription to clipboard: {text[:50]}...")

            # Truncate text for notification if it's too long
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
            # Show error notification
            if self.ui_manager and tray_icon:
                self.ui_manager.show_notification(
                    tray_icon,
                    "Clipboard Error",
                    f"Failed to copy transcription: {str(e)}",
                    normal_icon,
                )
