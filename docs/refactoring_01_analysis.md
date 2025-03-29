# Syllablaze Refactoring Analysis

## 1. DRY (Don't Repeat Yourself) Principle Violations

### 1.1. Duplicated Audio Processing Logic

**Issue:** There's significant code duplication between `_process_recording()` and `save_audio()` methods in `recorder.py`.

**Example:**
```python
# In recorder.py - Duplicated code in two methods
def _process_recording(self):
    # Lines 268-301
    audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
    
    if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
        # Logic to determine sample rate
        # ...
    else:
        original_rate = self.current_sample_rate
        
    # Resampling logic
    if original_rate != WHISPER_SAMPLE_RATE:
        # Resampling code
        # ...
    else:
        logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
    
    # Normalize audio data
    audio_data = audio_data.astype(np.float32) / 32768.0
    
def save_audio(self, filename):
    # Lines 307-348
    # Almost identical code as above
    audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
    
    if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
        # Same logic to determine sample rate
        # ...
    else:
        original_rate = self.current_sample_rate
        
    # Same resampling logic
    if original_rate != WHISPER_SAMPLE_RATE:
        # Same resampling code
        # ...
    else:
        logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
```

**Solution:** Extract the common audio processing logic into a separate method:

```python
def _process_audio_data(self):
    """Process recorded audio data and return processed numpy array"""
    audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
    
    if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
        logger.warning("No sample rate information available, assuming device default")
        if self.current_device_info is not None:
            original_rate = int(self.current_device_info['defaultSampleRate'])
        else:
            # If no device info is available, we have to use a reasonable default
            # Get the default input device's sample rate
            original_rate = int(self.audio.get_default_input_device_info()['defaultSampleRate'])
    else:
        original_rate = self.current_sample_rate
        
    # Resampling logic
    if original_rate != WHISPER_SAMPLE_RATE:
        logger.info(f"Resampling audio from {original_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
        # Calculate resampling ratio
        ratio = WHISPER_SAMPLE_RATE / original_rate
        output_length = int(len(audio_data) * ratio)
        
        # Resample audio
        audio_data = signal.resample(audio_data, output_length)
    else:
        logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
    
    return audio_data

def _process_recording(self):
    """Process the recording and keep it in memory"""
    try:
        logger.info("Processing recording in memory...")
        audio_data = self._process_audio_data()
        
        # Normalize the audio data to float32 in the range [-1.0, 1.0] as expected by Whisper
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        logger.info("Recording processed in memory")
        self.recording_finished.emit(audio_data)
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        self.recording_error.emit(f"Failed to process recording: {e}")

def save_audio(self, filename):
    """Save recorded audio to a WAV file"""
    try:
        audio_data = self._process_audio_data()
        
        # Save to WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(WHISPER_SAMPLE_RATE)  # Always save at 16000Hz for Whisper
        wf.writeframes(audio_data.astype(np.int16).tobytes())
        wf.close()
        
        # Log the saved file location
        logger.info(f"Recording saved to: {os.path.abspath(filename)}")
        
    except Exception as e:
        logger.error(f"Failed to save audio file: {e}")
        raise
```

### 1.2. Duplicated Transcription Logic

**Issue:** There's duplication between `transcribe()` and `transcribe_file()` methods in `transcriber.py`.

**Example:**
```python
# In transcriber.py
def transcribe(self, audio_data):
    """Transcribe audio data directly from memory"""
    try:
        # Check if model needs to be reloaded due to settings changes
        self.reload_model_if_needed()
        
        # Check if language has changed
        current_language = self.settings.get('language', 'auto')
        if current_language != self.current_language:
            self.current_language = current_language
        
        # Emit progress update
        self.transcription_progress.emit("Processing audio...")
        
        # Log the language being used for transcription
        lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
        logger.info(f"Transcribing with language: {lang_str}")
        logger.info(f"Using model: {self.current_model_name}")
        print(f"Transcribing with model: {self.current_model_name}, language: {lang_str}")
        
        # Run transcription with language setting
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=None if self.current_language == 'auto' else self.current_language
        )
        
        text = result["text"].strip()
        if not text:
            raise ValueError("No text was transcribed")
            
        self.transcription_progress.emit("Transcription completed!")
        logger.info(f"Transcribed text: [{text}]")
        self.transcription_finished.emit(text)
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        self.transcription_error.emit(str(e))

def transcribe_file(self, audio_data):
    """
    Transcribe audio data directly from memory
    
    Parameters:
    -----------
    audio_data: np.ndarray
        Audio data as a NumPy array, expected to be float32 in range [-1.0, 1.0]
    """
    if self.worker and self.worker.isRunning():
        logger.warning("Transcription already in progress")
        return
    
    # Check if model needs to be reloaded due to settings changes
    model_reloaded = self.reload_model_if_needed()
    if model_reloaded:
        logger.info("Model was reloaded due to settings change before transcription")
        print(f"Model reloaded to: {self.current_model_name}")
        
    # Check if language has changed
    current_language = self.settings.get('language', 'auto')
    if current_language != self.current_language:
        logger.info(f"Language changed from {self.current_language} to {current_language}, updating...")
        self.current_language = current_language
        print(f"Language changed to: {current_language}")
        
    # Emit initial progress status before starting worker
    self.transcription_progress.emit("Starting transcription...")
    self.transcription_progress_percent.emit(5)
        
    # Log the language being used for transcription
    lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
    logger.info(f"Transcription worker using language: {lang_str}")
    logger.info(f"Transcription worker using model: {self.current_model_name}")
    print(f"Transcribing audio with model: {self.current_model_name}, language: {lang_str}")
    
    # Use worker thread for transcription
    # ...
```

**Solution:** Extract common logic into helper methods and simplify the code:

```python
def _prepare_for_transcription(self):
    """Prepare for transcription by checking model and language settings"""
    # Check if model needs to be reloaded due to settings changes
    model_reloaded = self.reload_model_if_needed()
    
    # Check if language has changed
    current_language = self.settings.get('language', 'auto')
    language_changed = False
    if current_language != self.current_language:
        logger.info(f"Language changed from {self.current_language} to {current_language}, updating...")
        self.current_language = current_language
        language_changed = True
    
    # Log the language being used for transcription
    lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
    logger.info(f"Transcription using language: {lang_str}")
    logger.info(f"Transcription using model: {self.current_model_name}")
    
    return model_reloaded, language_changed, lang_str

def transcribe(self, audio_data):
    """Transcribe audio data directly from memory"""
    try:
        # Prepare for transcription
        _, _, lang_str = self._prepare_for_transcription()
        
        # Emit progress update
        self.transcription_progress.emit("Processing audio...")
        
        print(f"Transcribing with model: {self.current_model_name}, language: {lang_str}")
        
        # Run transcription with language setting
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=None if self.current_language == 'auto' else self.current_language
        )
        
        text = result["text"].strip()
        if not text:
            raise ValueError("No text was transcribed")
            
        self.transcription_progress.emit("Transcription completed!")
        logger.info(f"Transcribed text: [{text}]")
        self.transcription_finished.emit(text)
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        self.transcription_error.emit(str(e))

def transcribe_file(self, audio_data):
    """Transcribe audio data using a worker thread"""
    if self.worker and self.worker.isRunning():
        logger.warning("Transcription already in progress")
        return
    
    # Prepare for transcription
    model_reloaded, language_changed, lang_str = self._prepare_for_transcription()
    
    # Log changes if any occurred
    if model_reloaded:
        logger.info("Model was reloaded due to settings change before transcription")
        print(f"Model reloaded to: {self.current_model_name}")
        
    if language_changed:
        print(f"Language changed to: {self.current_language}")
    
    # Emit initial progress status before starting worker
    self.transcription_progress.emit("Starting transcription...")
    self.transcription_progress_percent.emit(5)
    
    print(f"Transcribing audio with model: {self.current_model_name}, language: {lang_str}")
    
    # Use worker thread for transcription
    # ...
```

### 1.3. Duplicated Window Positioning Logic

**Issue:** Window positioning code is duplicated across multiple window classes.

**Example:**
```python
# In progress_window.py
# Center the window
screen = QApplication.primaryScreen().geometry()
self.move(
    screen.center().x() - self.width() // 2,
    screen.center().y() - self.height() // 2
)

# In processing_window.py
# Center the window
screen = QApplication.primaryScreen().geometry()
self.move(
    screen.center().x() - self.width() // 2,
    screen.center().y() - self.height() // 2
)

# In loading_window.py
# Similar centering code
```

**Solution:** Create a utility module with a window positioning function:

```python
# Create a new file: blaze/utils.py
from PyQt6.QtWidgets import QApplication, QWidget

def center_window(window: QWidget):
    """Center a window on the screen"""
    screen = QApplication.primaryScreen().geometry()
    window.move(
        screen.center().x() - window.width() // 2,
        screen.center().y() - window.height() // 2
    )
```

Then use this in all window classes:

```python
from blaze.utils import center_window

# In window initialization
center_window(self)
```

## 2. Single Responsibility Principle Adherence

### 2.1. TrayRecorder Class Has Too Many Responsibilities

**Issue:** The `TrayRecorder` class in `main.py` handles system tray functionality, recording management, transcription management, and UI coordination.

**Example:**
```python
# In main.py
class TrayRecorder(QSystemTrayIcon):
    # This class handles:
    # 1. System tray icon and menu
    # 2. Recording state management
    # 3. Transcription coordination
    # 4. Window management (progress, settings)
    # 5. Error handling
    # 6. Application lifecycle
    # ...
```

**Solution:** Split the class into smaller, focused classes:

```python
# Proposed refactoring:

# 1. TrayIcon class - Handles only system tray functionality
class TrayIcon(QSystemTrayIcon):
    recording_toggled = pyqtSignal(bool)  # Signal when recording is toggled
    settings_toggled = pyqtSignal()       # Signal when settings is toggled
    quit_requested = pyqtSignal()         # Signal when quit is requested
    
    def __init__(self):
        super().__init__()
        self.setup_icon()
        self.setup_menu()
        
    def setup_icon(self):
        # Icon setup code
        pass
        
    def setup_menu(self):
        # Menu setup code
        pass
        
    def update_tooltip(self, info_dict):
        # Update tooltip with provided info
        pass
        
    def set_recording_state(self, is_recording):
        # Update icon and menu based on recording state
        pass

# 2. RecordingManager class - Handles recording functionality
class RecordingManager(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_processed = pyqtSignal(object)  # Emits processed audio data
    recording_error = pyqtSignal(str)
    volume_updated = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.setup_connections()
        
    def setup_connections(self):
        # Connect recorder signals
        pass
        
    def start_recording(self):
        # Start recording logic
        pass
        
    def stop_recording(self):
        # Stop recording logic
        pass

# 3. TranscriptionManager class - Handles transcription functionality
class TranscriptionManager(QObject):
    transcription_started = pyqtSignal()
    transcription_progress = pyqtSignal(str, int)  # Status text and percentage
    transcription_finished = pyqtSignal(str)       # Transcribed text
    transcription_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.transcriber = WhisperTranscriber()
        self.setup_connections()
        
    def setup_connections(self):
        # Connect transcriber signals
        pass
        
    def transcribe(self, audio_data):
        # Transcription logic
        pass

# 4. ApplicationController class - Coordinates the application
class ApplicationController(QObject):
    def __init__(self):
        super().__init__()
        self.tray_icon = TrayIcon()
        self.recording_manager = RecordingManager()
        self.transcription_manager = TranscriptionManager()
        self.settings_window = None
        self.progress_window = None
        self.setup_connections()
        
    def setup_connections(self):
        # Connect all signals between components
        pass
        
    def toggle_recording(self):
        # Coordinate recording toggle
        pass
        
    def toggle_settings(self):
        # Show/hide settings window
        pass
        
    def quit_application(self):
        # Clean shutdown logic
        pass
```

### 2.2. Settings Class Mixes Storage and Validation

**Issue:** The `Settings` class in `settings.py` handles both storage and validation of settings.

**Example:**
```python
# In settings.py
class Settings:
    # Get valid models from whisper._MODELS
    VALID_MODELS = list(whisper._MODELS.keys()) if hasattr(whisper, '_MODELS') else []
    # List of valid language codes for Whisper
    VALID_LANGUAGES = VALID_LANGUAGES
    # Valid sample rate modes
    VALID_SAMPLE_RATE_MODES = [SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE]
    
    def __init__(self):
        self.settings = QSettings(APP_NAME, APP_NAME)
        
    def get(self, key, default=None):
        value = self.settings.value(key, default)
        
        # Validate specific settings
        if key == 'model' and value not in self.VALID_MODELS:
            logger.warning(f"Invalid model in settings: {value}, using default: {default}")
            return default
        elif key == 'mic_index':
            try:
                return int(value)
            except (ValueError, TypeError):
                logger.warning(f"Invalid mic_index in settings: {value}, using default: {default}")
                return default
        # More validation...
```

**Solution:** Separate storage and validation concerns:

```python
# Create a validators.py file
class SettingsValidator:
    @staticmethod
    def validate_model(value, default):
        import whisper
        valid_models = list(whisper._MODELS.keys()) if hasattr(whisper, '_MODELS') else []
        if value not in valid_models:
            logger.warning(f"Invalid model in settings: {value}, using default: {default}")
            return default
        return value
        
    @staticmethod
    def validate_mic_index(value, default):
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid mic_index in settings: {value}, using default: {default}")
            return default
    
    @staticmethod
    def validate_language(value, default='auto'):
        from blaze.constants import VALID_LANGUAGES
        if value not in VALID_LANGUAGES:
            logger.warning(f"Invalid language in settings: {value}, using default: auto")
            return 'auto'
        return value
        
    @staticmethod
    def validate_sample_rate_mode(value, default):
        from blaze.constants import SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE, DEFAULT_SAMPLE_RATE_MODE
        valid_modes = [SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE]
        if value not in valid_modes:
            logger.warning(f"Invalid sample_rate_mode in settings: {value}, using default: {DEFAULT_SAMPLE_RATE_MODE}")
            return DEFAULT_SAMPLE_RATE_MODE
        return value

# Refactored Settings class
class Settings:
    def __init__(self):
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.validator = SettingsValidator()
        
    def get(self, key, default=None):
        value = self.settings.value(key, default)
        
        # Use validator methods based on key
        if key == 'model':
            return self.validator.validate_model(value, default)
        elif key == 'mic_index':
            return self.validator.validate_mic_index(value, default)
        elif key == 'language':
            return self.validator.validate_language(value, default)
        elif key == 'sample_rate_mode':
            return self.validator.validate_sample_rate_mode(value, default)
        
        # Log the settings access for important settings
        if key in ['model', 'language', 'sample_rate_mode']:
            logger.info(f"Setting accessed: {key} = {value}")
                
        return value
```

## 3. Code Modularity and Cohesion

### 3.1. Improve Module Organization

**Issue:** Some functionality is not properly modularized, making the code harder to maintain.

**Solution:** Reorganize the code into more focused modules:

```
blaze/
  __init__.py
  constants.py
  main.py
  
  # UI Components
  ui/
    __init__.py
    loading_window.py
    progress_window.py
    processing_window.py
    settings_window.py
    volume_meter.py
    
  # Core Functionality
  core/
    __init__.py
    recorder.py
    transcriber.py
    settings.py
    
  # Utilities
  utils/
    __init__.py
    audio_utils.py
    clipboard_manager.py
    whisper_model_manager.py
    ui_utils.py  # For common UI functions like centering windows
```

### 3.2. Extract Common UI Components

**Issue:** UI components like progress bars and status labels are duplicated across window classes.

**Solution:** Create reusable UI components:

```python
# In ui/components.py
class StatusBar(QWidget):
    """A reusable status bar with label and progress bar"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
    def set_status(self, text):
        self.status_label.setText(text)
        
    def set_progress(self, value):
        self.progress_bar.setValue(value)
        
    def set_indeterminate(self, indeterminate=True):
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
```

Then use this component in window classes:

```python
from blaze.ui.components import StatusBar

# In window initialization
self.status_bar = StatusBar()
layout.addWidget(self.status_bar)

# Later in code
self.status_bar.set_status("Processing...")
self.status_bar.set_progress(50)
```

## 4. Appropriate Abstraction Levels

### 4.1. Abstract Audio Processing

**Issue:** Low-level audio processing details are mixed with higher-level recording logic in `recorder.py`.

**Solution:** Create an abstraction layer for audio processing:

```python
# In audio_utils.py
class AudioProcessor:
    @staticmethod
    def convert_to_whisper_format(audio_data, original_rate):
        """Convert audio data to the format expected by Whisper"""
        # Resample if needed
        if original_rate != WHISPER_SAMPLE_RATE:
            logger.info(f"Resampling audio from {original_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
            ratio = WHISPER_SAMPLE_RATE / original_rate
            output_length = int(len(audio_data) * ratio)
            audio_data = signal.resample(audio_data, output_length)
        
        # Normalize to float32 in range [-1.0, 1.0]
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        return audio_data
    
    @staticmethod
    def save_to_wav(audio_data, filename, sample_rate, channels=1, sample_width=2):
        """Save audio data to a WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
        wf.close()
```

Then use this in the recorder:

```python
from blaze.utils.audio_utils import AudioProcessor

def _process_recording(self):
    try:
        logger.info("Processing recording in memory...")
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
        
        # Get original sample rate
        original_rate = self._get_original_sample_rate()
        
        # Process audio using the utility class
        processed_audio = AudioProcessor.convert_to_whisper_format(audio_data, original_rate)
        
        logger.info("Recording processed in memory")
        self.recording_finished.emit(processed_audio)
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        self.recording_error.emit(f"Failed to process recording: {e}")
```

### 4.2. Abstract Model Management

**Issue:** Whisper model management details are scattered across multiple files.

**Solution:** Create a more abstract model management interface:

```python
# In whisper_model_manager.py
class WhisperModelManager:
    """High-level interface for managing Whisper models"""
    
    @staticmethod
    def get_available_models():
        """Get list of all available models"""
        import whisper
        if hasattr(whisper, '_MODELS'):
            return list(whisper._MODELS.keys())
        return []
    
    @staticmethod
    def get_model_info():
        """Get comprehensive information about all models"""
        # Existing get_model_info implementation
        pass
    
    @staticmethod
    def get_model_path(model_name):
        """Get the file path for a specific model"""
        import os
        from pathlib import Path
        models_dir = os.path.join(Path.home(), ".cache", "whisper")
        return os.path.join(models_dir, f"{model_name}.pt")
    
    @staticmethod
    def is_model_downloaded(model_name):
        """Check if a model is downloaded"""
        model_path = WhisperModelManager.get_model_path(model_name)
        return os.path.exists(model_path)
    
    @staticmethod
    def download_model(model_name, progress_callback=None):
        """Download a model with progress updates"""
        # Implementation
        pass
    
    @staticmethod
    def delete_model(model_name):
        """Delete a model file"""
        model_path = WhisperModelManager.get_model_path(model_name)
        if os.path.exists(model_path):
            os.remove(model_path)
            return True
        return False
```

## 5. Excessive Coupling Between Components

### 5.1. Direct Import Coupling

**Issue:** Components directly import each other, creating tight coupling.

**Example:**
```python
# In settings_window.py
from blaze.main import update_tray_tooltip

# In whisper_model_manager.py
from blaze.main import update_tray_tooltip
```

**Solution:** Use a signal/event system for communication:

```python
# Create an events.py file
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """Central event bus for application-wide events"""
    settings_changed = pyqtSignal(str, object)  # key, value
    model_activated = pyqtSignal(str)           # model_name
    language_changed = pyqtSignal(str)          # language_code
    recording_state_changed = pyqtSignal(bool)  # is_recording
    
    # Singleton instance
    _instance = None
    
    @staticmethod
    def instance():
        if EventBus._instance is None:
            EventBus._instance = EventBus()
        return EventBus._instance

# Then in settings_window.py
from blaze.events import EventBus

def on_model_activated(self, model_name):
    # ...
    self.settings.set('model', model_name)
    # Emit event instead of direct function call
    EventBus.instance().model_activated.emit(model_name)

# In main.py
from blaze.events import EventBus

def initialize_event_handlers(self):
    # Connect to events
    EventBus.instance().model_activated.connect(self.on_model_activated)
    EventBus.instance().language_changed.connect(self.on_language_changed)
    
def on_model_activated(self, model_name):
    # Update tray tooltip
    self.update_tooltip()
```

### 5.2. Tight Coupling to Whisper Implementation

**Issue:** The code is tightly coupled to the specific Whisper implementation details.

**Solution:** Create an abstraction layer for transcription:

```python
# In transcriber.py
class TranscriptionEngine:
    """Abstract base class for transcription engines"""
    
    def __init__(self):
        pass
        
    def load_model(self, model_name):
        """Load a model by name"""
        raise NotImplementedError
        
    def transcribe(self, audio_data, language=None):
        """Transcribe audio data to text"""
        raise NotImplementedError
        
    def get_available_models(self):
        """Get list of available models"""
        raise NotImplementedError
        
    def get_available_languages(self):
        """Get list of available languages"""
        raise NotImplementedError

class WhisperTranscriptionEngine(TranscriptionEngine):
    """Whisper implementation of the transcription engine"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.model_name = None
        
    def load_model(self, model_name):
        import whisper
        self.model = whisper.load_model(model_name)
        self.model_name = model_name
        
    def transcribe(self, audio_data, language=None):
        if self.model is None:
            raise ValueError("Model not loaded")
            
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=language
        )
        
        return result["text"].strip()
        
    def get_available_models(self):
        import whisper
        if hasattr(whisper, '_MODELS'):
            return list(whisper._MODELS.keys())
        return []
        
    def get_available_languages(self):
        # Return Whisper's supported languages
        from blaze.constants import VALID_LANGUAGES
        return VALID_LANGUAGES
```

Then use this abstraction in the application:

