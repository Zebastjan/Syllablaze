"""
UI Manager for Syllablaze

This module provides a centralized manager for UI-related operations,
reducing code duplication and improving maintainability.
"""

from PyQt6.QtWidgets import QApplication, QMessageBox
import logging

logger = logging.getLogger(__name__)

class UIManager:
    """Manager class for UI-related operations"""
    
    def __init__(self):
        """Initialize the UI manager"""
        self.windows = {}  # Store references to windows
    
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