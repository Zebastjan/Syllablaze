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