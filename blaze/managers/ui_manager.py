"""
UI Manager for Syllablaze

This module provides a centralized manager for UI-related operations,
reducing code duplication and improving maintainability.
"""

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
import logging
import os

logger = logging.getLogger(__name__)

class UIManager:
    """Manager class for UI-related operations"""

    def __init__(self):
        """Initialize the UI manager"""
        self.windows = {}  # Store references to windows
        self.progress_window = None  # Current progress window
        self.normal_icon = None  # Normal tray icon
        self.recording_icon = None  # Recording tray icon
    
    def update_loading_status(self, window, message, progress, process_events=True):
        """Update loading window status and progress
        
        Parameters:
        -----------
        window : LoadingWindow
            The loading window to update
        message : str
            Status message to display
        progress : int
            Progress value (0-100)
        process_events : bool
            Whether to process application events after update
        """
        if not window:
            return
            
        try:
            window.set_status(message)
            window.set_progress(progress)
            
            if process_events:
                QApplication.processEvents()
        except Exception as e:
            logger.error(f"Error updating loading status: {e}")
    
    def safely_close_window(self, window, window_name=""):
        """Safely close a window with error handling
        
        Parameters:
        -----------
        window : QWidget
            The window to close
        window_name : str
            Name of the window for logging purposes
        
        Returns:
        --------
        bool
            True if window was closed successfully, False otherwise
        """
        if not window:
            return True
            
        try:
            logger.info(f"Closing {window_name} window")
            
            # Reset any processing state if it exists
            if hasattr(window, 'processing'):
                window.processing = False
            
            # Hide first to give immediate visual feedback
            window.hide()
            
            # Then close and schedule for deletion
            window.close()
            window.deleteLater()
            
            # Force an immediate process of events
            QApplication.processEvents()
            
            return True
        except Exception as e:
            logger.error(f"Error closing {window_name} window: {e}")
            return False
    
    def show_notification(self, tray, title, message, icon=None):
        """Show a system tray notification
        
        Parameters:
        -----------
        tray : QSystemTrayIcon
            The system tray icon to use for notification
        title : str
            Notification title
        message : str
            Notification message
        icon : QIcon
            Icon to use for notification (optional)
        """
        if not tray:
            return
            
        try:
            tray.showMessage(title, message, icon or tray.icon())
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def show_error_message(self, title, message, parent=None):
        """Show an error message dialog
        
        Parameters:
        -----------
        title : str
            Dialog title
        message : str
            Error message
        parent : QWidget
            Parent widget (optional)
        """
        try:
            QMessageBox.critical(parent, title, message)
        except Exception as e:
            logger.error(f"Error showing error message: {e}")
            # Fall back to console output if UI fails
            print(f"ERROR: {title} - {message}")
    
    def show_warning_message(self, title, message, parent=None):
        """Show a warning message dialog

        Parameters:
        -----------
        title : str
            Dialog title
        message : str
            Warning message
        parent : QWidget
            Parent widget (optional)
        """
        try:
            QMessageBox.warning(parent, title, message)
        except Exception as e:
            logger.error(f"Error showing warning message: {e}")
            # Fall back to console output if UI fails
            print(f"WARNING: {title} - {message}")

    def initialize_icons(self, app_icon):
        """Initialize tray icons

        Parameters:
        -----------
        app_icon : QIcon
            Application icon to use for normal state
        """
        self.normal_icon = app_icon
        self.recording_icon = QIcon.fromTheme("media-playback-stop")
        logger.info("Tray icons initialized")

    def create_progress_window(self, settings, title):
        """Create and return a progress window

        Parameters:
        -----------
        settings : Settings
            Application settings
        title : str
            Window title

        Returns:
        --------
        ProgressWindow or None
            Created progress window, or None if disabled in settings
        """
        from blaze.progress_window import ProgressWindow

        # Check if progress window should be shown
        show_progress = settings.get("show_progress_window", True)
        logger.info(f"Progress window setting: show_progress_window = {show_progress}")

        if not show_progress:
            logger.info("Progress window disabled in settings")
            return None

        # Close any existing window first
        if self.progress_window:
            self.safely_close_window(self.progress_window, "before new recording")
            self.progress_window = None

        # Create new progress window
        self.progress_window = ProgressWindow(settings, title)
        logger.info(f"Progress window created with title: {title}")
        return self.progress_window

    def get_progress_window(self):
        """Get current progress window

        Returns:
        --------
        ProgressWindow or None
            Current progress window reference
        """
        return self.progress_window

    def close_progress_window(self, context=""):
        """Close progress window if it exists

        Parameters:
        -----------
        context : str
            Context description for logging
        """
        if self.progress_window:
            self.safely_close_window(
                self.progress_window, f"progress {context}"
            )
            self.progress_window = None
            logger.info(f"Progress window closed (context: {context})")
        else:
            logger.debug(f"No progress window to close (context: {context})")

    def update_tray_icon_state(self, is_recording, tray_icon, normal_icon=None, recording_icon=None):
        """Update tray icon based on recording state

        Parameters:
        -----------
        is_recording : bool
            True if currently recording
        tray_icon : QSystemTrayIcon
            Tray icon to update
        normal_icon : QIcon (optional)
            Icon to use for normal state (uses stored icon if not provided)
        recording_icon : QIcon (optional)
            Icon to use for recording state (uses stored icon if not provided)
        """
        if not tray_icon:
            return

        # Use provided icons or fall back to stored ones
        normal = normal_icon or self.normal_icon
        recording = recording_icon or self.recording_icon

        if is_recording:
            tray_icon.setIcon(recording)
            logger.debug("Tray icon set to recording state")
        else:
            tray_icon.setIcon(normal)
            logger.debug("Tray icon set to normal state")

    def get_tooltip_text(self, settings, model=None, language=None, recognized_text=None):
        """Generate tooltip text for tray icon

        Parameters:
        -----------
        settings : Settings
            Application settings
        model : str (optional)
            Model name (fetched from settings if not provided)
        language : str (optional)
            Language code (fetched from settings if not provided)
        recognized_text : str (optional)
            Recently recognized text to include

        Returns:
        --------
        str
            Formatted tooltip text
        """
        from blaze.constants import APP_NAME, APP_VERSION, DEFAULT_WHISPER_MODEL, VALID_LANGUAGES

        # Get model and language from settings if not provided
        if model is None:
            model = settings.get("model", DEFAULT_WHISPER_MODEL)
        if language is None:
            language = settings.get("language", "auto")

        # Get language display name
        if language in VALID_LANGUAGES:
            language_display = f"Language: {VALID_LANGUAGES[language]}"
        else:
            language_display = (
                "Language: auto-detect"
                if language == "auto"
                else f"Language: {language}"
            )

        tooltip = f"{APP_NAME} {APP_VERSION}\nModel: {model}\n{language_display}"

        # Add recognized text if provided
        if recognized_text:
            max_length = 100
            if len(recognized_text) > max_length:
                recognized_text = recognized_text[:max_length] + "..."
            tooltip += f"\nRecognized: {recognized_text}"

        return tooltip

    def update_menu_action_text(self, action, is_recording, text_when_recording, text_when_not_recording):
        """Update menu action text based on state

        Parameters:
        -----------
        action : QAction
            Menu action to update
        is_recording : bool
            True if currently recording
        text_when_recording : str
            Text to show when recording
        text_when_not_recording : str
            Text to show when not recording
        """
        if not action:
            return

        if is_recording:
            action.setText(text_when_recording)
        else:
            action.setText(text_when_not_recording)