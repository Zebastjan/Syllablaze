# Structured Exception Hierarchy

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