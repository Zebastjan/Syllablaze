from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QApplication
import subprocess
import logging

logger = logging.getLogger(__name__)

class ClipboardManager(QObject):
    """Manages clipboard operations for transcribed text."""

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
        
    def paste_text(self, text):
        if not text:
            logger.warning("Received empty text, skipping clipboard operation")
            return
            
        logger.info(f"Copying text to clipboard: {text[:50]}...")
        self.clipboard.setText(text)
        
        # If set to paste to active window, simulate Ctrl+V
        if self.should_paste_to_active_window():
            self.paste_to_active_window()
    
        
    def paste_to_active_window(self):
        try:
            # Use xdotool to simulate Ctrl+V
            subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
        except Exception as e:
            logger.error(f"Failed to paste to active window: {e}")

    def should_paste_to_active_window(self):
        # TODO: Get this from settings
        return False

    @pyqtSlot(str)
    def copy_to_clipboard(self, text, tray_icon=None, normal_icon=None):
        """Copy transcribed text to clipboard and show notification.

        This is the main method called when transcription completes.

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
            # Copy text to clipboard
            self.clipboard.setText(text)
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
                    normal_icon
                )

