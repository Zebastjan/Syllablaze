# Excessive Coupling Between Components

## 5.1. Direct Import Coupling

**Issue:** Components directly import each other, creating tight coupling.

**Example:**
```python
# In settings_window.py
from blaze.main import update_tray_tooltip

# In whisper_model_manager.py
from blaze.main import update_tray_tooltip

# In settings_window.py
def on_model_activated(self, model_name):
    # ...
    # Import and use the update_tray_tooltip function
    from blaze.main import update_tray_tooltip
    update_tray_tooltip()
```

This creates a circular dependency where:
- `main.py` imports `settings_window.py` to create the settings window
- `settings_window.py` imports `main.py` to update the tray tooltip

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
    tooltip_update_requested = pyqtSignal()     # Request to update tooltip
    
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
    # Request tooltip update
    EventBus.instance().tooltip_update_requested.emit()

# In main.py
from blaze.events import EventBus

def initialize_event_handlers(self):
    # Connect to events
    EventBus.instance().model_activated.connect(self.on_model_activated)
    EventBus.instance().language_changed.connect(self.on_language_changed)
    EventBus.instance().tooltip_update_requested.connect(self.update_tooltip)
    
def on_model_activated(self, model_name):
    # Handle model activation
    pass
    
def update_tooltip(self):
    # Update tray tooltip
    pass
```

## 5.2. Tight Coupling to Whisper Implementation

**Issue:** The code is tightly coupled to the specific Whisper implementation details.

**Example:**
```python
# In transcriber.py
def transcribe(self, audio_data):
    """Transcribe audio data directly from memory"""
    try:
        # ...
        
        # Run transcription with language setting
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=None if self.current_language == 'auto' else self.current_language
        )
        
        text = result["text"].strip()
        # ...
    except Exception as e:
        # ...

# In settings.py
class Settings:
    # Get valid models from whisper._MODELS
    VALID_MODELS = list(whisper._MODELS.keys()) if hasattr(whisper, '_MODELS') else []
```

**Solution:** Create an abstraction layer for transcription:

```python
# In core/transcription.py
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
        return self.model
        
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

```python
# In transcriber.py
from blaze.core.transcription import WhisperTranscriptionEngine

class WhisperTranscriber(QObject):
    # ...
    
    def __init__(self):
        super().__init__()
        self.engine = WhisperTranscriptionEngine()
        self.worker = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.settings = Settings()
        self.current_language = self.settings.get('language', 'auto')
        self.load_model()
        
    def load_model(self):
        """Load the Whisper model based on current settings"""
        try:
            model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
            logger.info(f"Loading Whisper model: {model_name}")
            
            # Store the current model name for reference
            self.current_model_name = model_name
            
            # Load the model using the engine
            self.engine.load_model(model_name)
            
            # Update and log the current language setting
            self.current_language = self.settings.get('language', 'auto')
            lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
            logger.info(f"Current language setting: {lang_str}")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
            
    def transcribe(self, audio_data):
        """Transcribe audio data directly from memory"""
        try:
            # Prepare for transcription
            self.reload_model_if_needed()
            
            # Emit progress update
            self.transcription_progress.emit("Processing audio...")
            
            # Get language parameter
            language = None if self.current_language == 'auto' else self.current_language
            
            # Use the engine to transcribe
            text = self.engine.transcribe(audio_data, language)
            
            if not text:
                raise ValueError("No text was transcribed")
                
            self.transcription_progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: [{text}]")
            self.transcription_finished.emit(text)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.transcription_error.emit(str(e))
```

## 5.3. UI Components Directly Accessing Settings

**Issue:** UI components directly access the Settings class, creating tight coupling.

**Example:**
```python
# In progress_window.py
def __init__(self, title="Recording"):
    # ...
    
    # Get settings
    self.settings = Settings()
    
    # Get current settings
    model_name = self.settings.get('model', 'tiny')
    language = self.settings.get('language', 'auto')
    # ...

# In settings_window.py
def on_language_changed(self, index):
    language_code = self.lang_combo.currentData()
    language_name = self.lang_combo.currentText()
    try:
        # Set the language
        self.settings.set('language', language_code)
        
        # Update any active transcriber instances
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'transcriber') and widget.transcriber:
                widget.transcriber.update_language(language_code)
        
        # Import and use the update_tray_tooltip function
        from blaze.main import update_tray_tooltip
        update_tray_tooltip()
        
        # Log confirmation that the change was successful
        logger.info(f"Language successfully changed to: {language_name} ({language_code})")
        print(f"Language successfully changed to: {language_name} ({language_code})", flush=True)
    except ValueError as e:
        logger.error(f"Failed to set language: {e}")
        QMessageBox.warning(self, "Error", str(e))
```

**Solution:** Create a settings service that UI components can depend on:

```python
# In core/settings_service.py
class SettingsService:
    """Service for accessing application settings"""
    
    def __init__(self, settings=None):
        self.settings = settings or Settings()
        self.event_bus = EventBus.instance()
        
    def get_model(self):
        """Get the current model name"""
        return self.settings.get('model', DEFAULT_WHISPER_MODEL)
        
    def set_model(self, model_name):
        """Set the current model name"""
        self.settings.set('model', model_name)
        self.event_bus.settings_changed.emit('model', model_name)
        self.event_bus.model_activated.emit(model_name)
        
    def get_language(self):
        """Get the current language code"""
        return self.settings.get('language', 'auto')
        
    def set_language(self, language_code):
        """Set the current language code"""
        self.settings.set('language', language_code)
        self.event_bus.settings_changed.emit('language', language_code)
        self.event_bus.language_changed.emit(language_code)
        
    def get_mic_index(self):
        """Get the current microphone index"""
        return self.settings.get('mic_index', 0)
        
    def set_mic_index(self, mic_index):
        """Set the current microphone index"""
        self.settings.set('mic_index', mic_index)
        self.event_bus.settings_changed.emit('mic_index', mic_index)
        
    def get_sample_rate_mode(self):
        """Get the current sample rate mode"""
        return self.settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        
    def set_sample_rate_mode(self, mode):
        """Set the current sample rate mode"""
        self.settings.set('sample_rate_mode', mode)
        self.event_bus.settings_changed.emit('sample_rate_mode', mode)
```

Then use this service in UI components:

```python
# In progress_window.py
def __init__(self, title="Recording", settings_service=None):
    # ...
    
    # Get settings service
    self.settings_service = settings_service or SettingsService()
    
    # Get current settings
    model_name = self.settings_service.get_model()
    language = self.settings_service.get_language()
    # ...

# In settings_window.py
def __init__(self, settings_service=None):
    # ...
    
    # Get settings service
    self.settings_service = settings_service or SettingsService()
    
    # ...
    
def on_language_changed(self, index):
    language_code = self.lang_combo.currentData()
    language_name = self.lang_combo.currentText()
    try:
        # Set the language using the service
        self.settings_service.set_language(language_code)
        
        # Log confirmation that the change was successful
        logger.info(f"Language successfully changed to: {language_name} ({language_code})")
        print(f"Language successfully changed to: {language_name} ({language_code})", flush=True)
    except ValueError as e:
        logger.error(f"Failed to set language: {e}")
        QMessageBox.warning(self, "Error", str(e))
```

## 5.4. Direct Widget Access Across Components

**Issue:** Components directly access widgets in other components, creating tight coupling.

**Example:**
```python
# In main.py
def update_volume_meter(self, value):
    # Update debug window first
    if hasattr(self, 'debug_window'):
        self.debug_window.update_values(value)
        
    # Then update volume meter as before
    if self.progress_window and self.recording:
        self.progress_window.update_volume(value)

# In settings_window.py
def on_language_changed(self, index):
    # ...
    
    # Update any active transcriber instances
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if hasattr(widget, 'transcriber') and widget.transcriber:
            widget.transcriber.update_language(language_code)
```

**Solution:** Use the event bus for communication between components:

```python
# In events.py
class EventBus(QObject):
    # ...
    volume_updated = pyqtSignal(float)  # Volume level
    # ...

# In main.py
def initialize_event_handlers(self):
    # ...
    
    # Connect recorder volume signal to event bus
    self.recorder.volume_updated.connect(self.on_volume_updated)
    
    # Connect event bus volume signal to UI update
    EventBus.instance().volume_updated.connect(self.update_volume_meter)
    
def on_volume_updated(self, value):
    # Forward to event bus
    EventBus.instance().volume_updated.emit(value)
    
def update_volume_meter(self, value):
    # Update volume meter if window exists
    if self.progress_window and self.recording:
        self.progress_window.update_volume(value)

# In debug_window.py
def __init__(self):
    # ...
    
    # Connect to event bus
    EventBus.instance().volume_updated.connect(self.update_values)
```

This approach decouples the components by removing direct references between them. Each component only needs to know about the event bus, not about other components.