# Error Handling Consistency

## 9.1. Inconsistent Error Handling Approaches

**Issue:** The codebase uses multiple approaches to error handling, including direct exception handling, error signals, and error messages.

**Example:**
```python
# In main.py - Using try-except with error logging
try:
    self.recorder.stop_recording()
except Exception as e:
    logger.error(f"Error stopping recording: {e}")
    if self.progress_window:
        self.progress_window.close()
        self.progress_window = None
    return

# In transcriber.py - Using try-except with error signal
try:
    # ...
    result = self.model.transcribe(
        audio_data,
        fp16=False,
        language=None if self.current_language == 'auto' else self.current_language
    )
    # ...
except Exception as e:
    logger.error(f"Transcription failed: {e}")
    self.transcription_error.emit(str(e))

# In settings.py - Using validation with ValueError
def set(self, key, value):
    # Validate before saving
    if key == 'model' and value not in self.VALID_MODELS:
        raise ValueError(f"Invalid model: {value}")
    # ...
```

**Solution:** Implement a consistent error handling strategy:

```python
# Create an error_handling.py file
class ApplicationError(Exception):
    """Base class for all application errors"""
    def __init__(self, message, error_code=None, original_exception=None):
        self.message = message
        self.error_code = error_code
        self.original_exception = original_exception
        super().__init__(self.message)

class RecordingError(ApplicationError):
    """Error related to audio recording"""
    pass

class TranscriptionError(ApplicationError):
    """Error related to transcription"""
    pass

class SettingsError(ApplicationError):
    """Error related to application settings"""
    pass

class ModelError(ApplicationError):
    """Error related to Whisper models"""
    pass

def handle_error(error, logger, error_signal=None):
    """Centralized error handling function"""
    # Log the error
    if isinstance(error, ApplicationError):
        logger.error(f"{error.__class__.__name__}: {error.message}")
        if error.original_exception:
            logger.debug(f"Original exception: {error.original_exception}")
    else:
        logger.error(f"Unexpected error: {str(error)}")
    
    # Emit error signal if provided
    if error_signal:
        if isinstance(error, ApplicationError):
            error_signal.emit(error.message)
        else:
            error_signal.emit(str(error))
    
    # Return the error for further handling if needed
    return error
```

Then use this consistent approach throughout the codebase:

```python
# In main.py
from blaze.error_handling import RecordingError, handle_error

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
                if self.progress_window:
                    self.progress_window.close()
                    self.progress_window = None
                return
    # ...

# In transcriber.py
from blaze.error_handling import TranscriptionError, handle_error

def transcribe(self, audio_data):
    """Transcribe audio data directly from memory"""
    try:
        # ...
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=None if self.current_language == 'auto' else self.current_language
        )
        # ...
    except Exception as e:
        error = TranscriptionError("Failed to transcribe audio", original_exception=e)
        handle_error(error, logger, self.transcription_error)

# In settings.py
from blaze.error_handling import SettingsError

def set(self, key, value):
    # Validate before saving
    if key == 'model' and value not in self.VALID_MODELS:
        raise SettingsError(f"Invalid model: {value}")
    # ...
```

## 9.2. Missing Error Recovery Mechanisms

**Issue:** Some error handling code doesn't include proper recovery mechanisms, potentially leaving the application in an inconsistent state.

**Example:**
```python
# In recorder.py
def start_recording(self):
    if self.is_recording:
        return
        
    try:
        self.frames = []
        self.is_recording = True
        
        # Get settings
        settings = Settings()
        mic_index = settings.get('mic_index')
        sample_rate_mode = settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        
        # ... more setup code ...
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=target_sample_rate,
            input=True,
            input_device_index=mic_index,
            frames_per_buffer=1024,
            stream_callback=self._callback
        )
        
        self.stream.start_stream()
        logger.info(f"Recording started at {self.current_sample_rate}Hz")
        
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        self.recording_error.emit(f"Failed to start recording: {e}")
        self.is_recording = False  # Only this flag is reset, but other state might be inconsistent
```

**Solution:** Implement proper recovery mechanisms:

```python
# In recorder.py
def start_recording(self):
    if self.is_recording:
        return
    
    # Save original state for recovery
    original_stream = self.stream
    
    try:
        # Reset state
        self.frames = []
        self.is_recording = True
        self.stream = None
        
        # Get settings
        settings = Settings()
        mic_index = settings.get('mic_index')
        sample_rate_mode = settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        
        # ... more setup code ...
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=target_sample_rate,
            input=True,
            input_device_index=mic_index,
            frames_per_buffer=1024,
            stream_callback=self._callback
        )
        
        self.stream.start_stream()
        logger.info(f"Recording started at {self.current_sample_rate}Hz")
        
    except Exception as e:
        # Full recovery to previous state
        self._recover_from_error(original_stream)
        
        # Create and handle error
        error = RecordingError(f"Failed to start recording: {str(e)}", original_exception=e)
        handle_error(error, logger, self.recording_error)
    
def _recover_from_error(self, original_stream):
    """Recover from an error by restoring previous state"""
    logger.info("Recovering from recording error")
    
    # Reset recording state
    self.is_recording = False
    self.frames = []
    
    # Close new stream if it was created
    if self.stream and self.stream != original_stream:
        try:
            self.stream.stop_stream()
            self.stream.close()
        except Exception as e:
            logger.warning(f"Error closing stream during recovery: {e}")
    
    # Restore original stream
    self.stream = original_stream
```

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
```

## 9.4. Lack of Structured Exception Hierarchy

**Issue:** The codebase doesn't have a structured exception hierarchy, making it difficult to catch and handle specific types of errors.

**Example:**
```python
# In various places, generic exceptions are used
except Exception as e:
    logger.error(f"Failed to start recording: {e}")
    self.recording_error.emit(f"Failed to start recording: {e}")
    
# In settings.py, ValueError is used for validation errors
if key == 'model' and value not in self.VALID_MODELS:
    raise ValueError(f"Invalid model: {value}")
```

**Solution:** Implement a structured exception hierarchy:

```python
# In error_handling.py
class ApplicationError(Exception):
    """Base class for all application errors"""
    def __init__(self, message, error_code=None, original_exception=None):
        self.message = message
        self.error_code = error_code
        self.original_exception = original_exception
        super().__init__(self.message)

# Audio-related errors
class AudioError(ApplicationError):
    """Base class for audio-related errors"""
    pass

class RecordingError(AudioError):
    """Error during audio recording"""
    pass

class PlaybackError(AudioError):
    """Error during audio playback"""
    pass

class AudioDeviceError(AudioError):
    """Error related to audio devices"""
    pass

# Transcription-related errors
class TranscriptionError(ApplicationError):
    """Base class for transcription-related errors"""
    pass

class ModelLoadError(TranscriptionError):
    """Error loading a transcription model"""
    pass

class ModelNotFoundError(TranscriptionError):
    """Error when a model is not found"""
    pass

class TranscriptionProcessError(TranscriptionError):
    """Error during the transcription process"""
    pass

# Settings-related errors
class SettingsError(ApplicationError):
    """Base class for settings-related errors"""
    pass

class ValidationError(SettingsError):
    """Error validating settings values"""
    pass

class PersistenceError(SettingsError):
    """Error persisting settings"""
    pass

# UI-related errors
class UIError(ApplicationError):
    """Base class for UI-related errors"""
    pass

class WindowError(UIError):
    """Error related to window management"""
    pass

class ResourceError(UIError):
    """Error loading UI resources"""
    pass
```

Then use these specific exception types throughout the codebase:

```python
# In recorder.py
from blaze.error_handling import RecordingError, AudioDeviceError

def start_recording(self):
    if self.is_recording:
        return
        
    try:
        self.frames = []
        self.is_recording = True
        
        # Get settings
        settings = Settings()
        mic_index = settings.get('mic_index')
        sample_rate_mode = settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        
        try:
            mic_index = int(mic_index) if mic_index is not None else None
        except (ValueError, TypeError):
            raise AudioDeviceError(f"Invalid microphone index: {mic_index}")
        
        # Get device info
        try:
            if mic_index is not None:
                device_info = self.audio.get_device_info_by_index(mic_index)
                logger.info(f"Using selected input device: {device_info['name']}")
            else:
                device_info = self.audio.get_default_input_device_info()
                logger.info(f"Using default input device: {device_info['name']}")
                mic_index = device_info['index']
        except Exception as e:
            raise AudioDeviceError(f"Failed to get device info: {str(e)}", original_exception=e)
        
        # ... more setup code ...
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=target_sample_rate,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=1024,
                stream_callback=self._callback
            )
        except Exception as e:
            raise RecordingError(f"Failed to open audio stream: {str(e)}", original_exception=e)
        
        try:
            self.stream.start_stream()
        except Exception as e:
            raise RecordingError(f"Failed to start audio stream: {str(e)}", original_exception=e)
            
        logger.info(f"Recording started at {self.current_sample_rate}Hz")
        
    except ApplicationError as e:
        # ApplicationError is already structured, just handle it
        logger.error(f"{e.__class__.__name__}: {e.message}")
        self.recording_error.emit(e.message)
        self.is_recording = False
    except Exception as e:
        # Wrap unexpected exceptions in RecordingError
        error = RecordingError(f"Unexpected error starting recording: {str(e)}", original_exception=e)
        logger.error(f"{error.__class__.__name__}: {error.message}")
        self.recording_error.emit(error.message)
        self.is_recording = False
```

This structured approach makes it easier to catch and handle specific types of errors, and provides more context about the error's source and nature.