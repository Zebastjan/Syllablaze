# Consistent Error Reporting to Users

## 9.3. Inconsistent Error Reporting to Users

**Issue:** Error reporting to users is inconsistent, with some errors shown in message boxes, some in notifications, and some only logged.

**Example:**
```python
# In main.py - Using QMessageBox
QMessageBox.critical(None, "Error",
    f"Failed to load Whisper model: {str(e)}\n\nPlease check Settings to download the model.")

# In main.py - Using system tray notification
self.showMessage("Recording Error",
                error,
                self.normal_icon)

# In settings_window.py - Using QMessageBox
QMessageBox.warning(self, "Error", str(e))

# In some places - Only logging without user notification
logger.error(f"Error waiting for transcription worker: {thread_error}")
```

**Solution:** Implement a consistent error reporting system:

```python
# Add to error_handling.py
from enum import Enum
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QIcon

class ErrorSeverity(Enum):
    """Enum for error severity levels"""
    INFO = 1      # Informational message, non-critical
    WARNING = 2   # Warning, operation can continue but with limitations
    ERROR = 3     # Error, operation failed but application can continue
    CRITICAL = 4  # Critical error, application may need to exit

class ErrorReporter:
    """Centralized error reporting to users"""
    
    @staticmethod
    def report_to_user(error, parent=None, severity=ErrorSeverity.ERROR, tray_icon=None):
        """Report an error to the user using the appropriate method"""
        # Get error message
        if isinstance(error, ApplicationError):
            message = error.message
        else:
            message = str(error)
        
        # Report based on severity and available UI
        if severity == ErrorSeverity.CRITICAL:
            # Always use message box for critical errors
            ErrorReporter._show_message_box(message, "Critical Error", QMessageBox.Icon.Critical, parent)
        elif severity == ErrorSeverity.ERROR:
            if parent and parent.isVisible():
                # Use message box if parent window is visible
                ErrorReporter._show_message_box(message, "Error", QMessageBox.Icon.Critical, parent)
            elif tray_icon:
                # Use tray notification if available
                ErrorReporter._show_tray_notification(message, "Error", tray_icon)
            else:
                # Fall back to message box
                ErrorReporter._show_message_box(message, "Error", QMessageBox.Icon.Critical, None)
        elif severity == ErrorSeverity.WARNING:
            if parent and parent.isVisible():
                # Use message box if parent window is visible
                ErrorReporter._show_message_box(message, "Warning", QMessageBox.Icon.Warning, parent)
            elif tray_icon:
                # Use tray notification if available
                ErrorReporter._show_tray_notification(message, "Warning", tray_icon)
            # For warnings, it's okay to not show anything if no UI is available
        elif severity == ErrorSeverity.INFO:
            # Only show info messages if we have a tray icon
            if tray_icon:
                ErrorReporter._show_tray_notification(message, "Information", tray_icon)
    
    @staticmethod
    def _show_message_box(message, title, icon, parent):
        """Show a message box with the error"""
        QMessageBox.critical(parent, title, message, icon)
    
    @staticmethod
    def _show_tray_notification(message, title, tray_icon):
        """Show a system tray notification with the error"""
        icon = QIcon.fromTheme("dialog-error")
        tray_icon.showMessage(title, message, icon)
```

Then use this consistent approach throughout the codebase:

```python
# In main.py
from blaze.error_handling import ErrorReporter, ErrorSeverity, RecordingError

def toggle_recording(self):
    if self.recording:
        # Stop recording
        self.recording = False
        self.record_action.setText("Start Recording")
        self.setIcon(self.normal_icon)
        
        # Update progress window before stopping recording
        if self.progress_window:
            self.progress_window.set_processing_mode()
            self.progress_window.set_status("Processing audio...")
        
        # Stop the actual recording
        if self.recorder:
            try:
                self.recorder.stop_recording()
            except Exception as e:
                error = RecordingError("Failed to stop recording", original_exception=e)
                handle_error(error, logger)
                ErrorReporter.report_to_user(error, self.progress_window, ErrorSeverity.ERROR, self)
                if self.progress_window:
                    self.progress_window.close()
                    self.progress_window = None
                return
    # ...

# In transcriber.py
def handle_transcription_error(self, error):
    """Handle transcription error in the UI"""
    # Create application error
    app_error = TranscriptionError(error)
    
    # Log the error
    handle_error(app_error, logger)
    
    # Report to user
    from blaze.main import get_tray_recorder
    tray = get_tray_recorder()
    ErrorReporter.report_to_user(app_error, None, ErrorSeverity.ERROR, tray)
    
    # Update tooltip to indicate error
    if tray:
        tray.update_tooltip()
    
    # Close progress window if open
    if tray and tray.progress_window:
        tray.progress_window.close()
        tray.progress_window = None