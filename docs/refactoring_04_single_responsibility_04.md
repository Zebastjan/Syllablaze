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