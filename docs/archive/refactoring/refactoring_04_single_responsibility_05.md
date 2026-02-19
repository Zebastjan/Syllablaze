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