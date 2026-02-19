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