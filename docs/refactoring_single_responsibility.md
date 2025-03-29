# Single Responsibility Principle Adherence

## 2.1. TrayRecorder Class Has Too Many Responsibilities

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

## 2.2. Settings Class Mixes Storage and Validation

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

## 2.3. Mixing UI and Business Logic in Window Classes

**Issue:** Window classes like `ProgressWindow` and `SettingsWindow` mix UI rendering with business logic.

**Example:**
```python
# In settings_window.py
def on_model_activated(self, model_name):
    """Handle model activation from the table"""
    if hasattr(self, 'current_model') and model_name == self.current_model:
        logger.info(f"Model {model_name} is already active, no change needed")
        print(f"Model {model_name} is already active, no change needed")
        return
        
    try:
        # Set the model
        self.settings.set('model', model_name)
        self.current_model = model_name
        
        # No modal dialog needed
        
        # Update any active transcriber instances
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'transcriber') and widget.transcriber:
                widget.transcriber.update_model(model_name)
        
        # Import and use the update_tray_tooltip function
        from blaze.main import update_tray_tooltip
        update_tray_tooltip()
        
        # Log confirmation that the change was successful
        logger.info(f"Model successfully changed to: {model_name}")
        print(f"Model successfully changed to: {model_name}")
                
        self.initialization_complete.emit()
    except ValueError as e:
        logger.error(f"Failed to set model: {e}")
        QMessageBox.warning(self, "Error", str(e))
```

**Solution:** Separate UI from business logic using a presenter pattern:

```python
# Create a presenter class
class SettingsPresenter:
    def __init__(self, view, settings_service):
        self.view = view
        self.settings_service = settings_service
        self.setup_connections()
        
    def setup_connections(self):
        # Connect view signals to presenter methods
        self.view.model_activated.connect(self.activate_model)
        self.view.language_changed.connect(self.change_language)
        
    def activate_model(self, model_name):
        """Handle model activation business logic"""
        try:
            # Check if already active
            if self.settings_service.get_current_model() == model_name:
                self.view.show_info(f"Model {model_name} is already active")
                return
                
            # Update the model in settings
            self.settings_service.set_model(model_name)
            
            # Notify other components via event bus
            from blaze.events import EventBus
            EventBus.instance().model_activated.emit(model_name)
            
            # Update view
            self.view.update_model_display(model_name)
            self.view.show_success(f"Model successfully changed to: {model_name}")
            
        except ValueError as e:
            self.view.show_error(f"Failed to set model: {str(e)}")

# Then in the view class
class SettingsWindow(QWidget):
    model_activated = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    
    def __init__(self, settings_service):
        super().__init__()
        self.presenter = SettingsPresenter(self, settings_service)
        self.setup_ui()
        
    def on_model_table_activated(self, model_name):
        # Just emit the signal, let the presenter handle the logic
        self.model_activated.emit(model_name)
        
    def update_model_display(self, model_name):
        # Update UI to reflect the new model
        pass
        
    def show_success(self, message):
        logger.info(message)
        print(message)
        
    def show_error(self, message):
        logger.error(message)
        QMessageBox.warning(self, "Error", message)
        
    def show_info(self, message):
        logger.info(message)
        print(message)