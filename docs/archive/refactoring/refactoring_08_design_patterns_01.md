## 8.1. Observer Pattern Enhancement

**Issue:** The application already uses the Observer pattern through Qt's signal/slot mechanism, but it's not consistently applied across all components.

**Example:**
```python
# In main.py
def update_tooltip(self, recognized_text=None):
    """Update the tooltip with app name, version, model and language information"""
    import sys
    
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    language_code = settings.get('language', 'auto')
    
    # Get language display name from VALID_LANGUAGES if available
    if language_code in VALID_LANGUAGES:
        language_display = f"Language: {VALID_LANGUAGES[language_code]}"
    else:
        language_display = "Language: auto-detect" if language_code == 'auto' else f"Language: {language_code}"
    
    tooltip = f"{APP_NAME} {APP_VERSION}\nModel: {model_name}\n{language_display}"
    
    # Add recognized text to tooltip if provided
    if recognized_text:
        # Truncate text if it's too long
        max_length = 100
        if len(recognized_text) > max_length:
            recognized_text = recognized_text[:max_length] + "..."
        tooltip += f"\nRecognized: {recognized_text}"
    
    # Print tooltip info to console with flush
    print(f"TOOLTIP UPDATE: MODEL={model_name}, {language_display}", flush=True)
    sys.stdout.flush()
        
    self.setToolTip(tooltip)

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

**Solution:** Implement a more consistent Observer pattern using a central event bus:

```python
# Create an events.py file
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """Central event bus for application-wide events"""
    # Settings events
    settings_changed = pyqtSignal(str, object)  # key, value
    model_activated = pyqtSignal(str)           # model_name
    language_changed = pyqtSignal(str)          # language_code
    
    # Recording events
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_completed = pyqtSignal(object)    # audio_data
    
    # Transcription events
    transcription_started = pyqtSignal()
    transcription_completed = pyqtSignal(str)   # transcribed_text
    
    # UI update events
    tooltip_update_needed = pyqtSignal(dict)    # tooltip_info
    
    # Singleton instance
    _instance = None
    
    @staticmethod
    def instance():
        if EventBus._instance is None:
            EventBus._instance = EventBus()
        return EventBus._instance

# In main.py
from blaze.events import EventBus

def __init__(self):
    super().__init__()
    # ...
    
    # Connect to event bus
    self._connect_to_event_bus()

def _connect_to_event_bus(self):
    event_bus = EventBus.instance()
    event_bus.model_activated.connect(self._on_model_changed)
    event_bus.language_changed.connect(self._on_language_changed)
    event_bus.tooltip_update_needed.connect(self._update_tooltip_from_info)
    event_bus.transcription_completed.connect(self._on_transcription_completed)
    
def _on_model_changed(self, model_name):
    self._update_tooltip()
    
def _on_language_changed(self, language_code):
    self._update_tooltip()
    
def _on_transcription_completed(self, text):
    self._update_tooltip(recognized_text=text)
    
def _update_tooltip(self, recognized_text=None):
    """Update the tooltip with app name, version, model and language information"""
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    language_code = settings.get('language', 'auto')
    
    # Get language display name from VALID_LANGUAGES if available
    if language_code in VALID_LANGUAGES:
        language_display = f"Language: {VALID_LANGUAGES[language_code]}"
    else:
        language_display = "Language: auto-detect" if language_code == 'auto' else f"Language: {language_code}"
    
    tooltip_info = {
        'app_name': APP_NAME,
        'app_version': APP_VERSION,
        'model_name': model_name,
        'language_display': language_display,
        'recognized_text': recognized_text
    }
    
    # Emit event for tooltip update
    EventBus.instance().tooltip_update_needed.emit(tooltip_info)
    
def _update_tooltip_from_info(self, info):
    """Update tooltip from provided info dictionary"""
    tooltip = f"{info['app_name']} {info['app_version']}\nModel: {info['model_name']}\n{info['language_display']}"
    
    # Add recognized text to tooltip if provided
    if info.get('recognized_text'):
        # Truncate text if it's too long
        recognized_text = info['recognized_text']
        max_length = 100
        if len(recognized_text) > max_length:
            recognized_text = recognized_text[:max_length] + "..."
        tooltip += f"\nRecognized: {recognized_text}"
    
    # Set the tooltip
    self.setToolTip(tooltip)

# In settings_window.py
from blaze.events import EventBus

def on_model_activated(self, model_name):
    """Handle model activation from the table"""
    if hasattr(self, 'current_model') and model_name == self.current_model:
        logger.info(f"Model {model_name} is already active, no change needed")
        return
        
    try:
        # Set the model
        self.settings.set('model', model_name)
        self.current_model = model_name
        
        # Emit event for model activation
        EventBus.instance().model_activated.emit(model_name)
        
        # Log confirmation that the change was successful
        logger.info(f"Model successfully changed to: {model_name}")
                
        self.initialization_complete.emit()
    except ValueError as e:
        logger.error(f"Failed to set model: {e}")
        QMessageBox.warning(self, "Error", str(e))