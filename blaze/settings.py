from PyQt6.QtCore import QSettings
from blaze.constants import (
    APP_NAME, VALID_LANGUAGES,
    SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE, DEFAULT_SAMPLE_RATE_MODE
)
import whisper
import logging

logger = logging.getLogger(__name__)

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
        elif key == 'language' and value not in self.VALID_LANGUAGES:
            logger.warning(f"Invalid language in settings: {value}, using default: auto")
            return 'auto'  # Default to auto-detect
        elif key == 'sample_rate_mode' and value not in self.VALID_SAMPLE_RATE_MODES:
            logger.warning(f"Invalid sample_rate_mode in settings: {value}, using default: {DEFAULT_SAMPLE_RATE_MODE}")
            return DEFAULT_SAMPLE_RATE_MODE
        
        # Log the settings access for important settings
        if key in ['model', 'language', 'sample_rate_mode']:
            logger.info(f"Setting accessed: {key} = {value}")
                
        return value
        
    def set(self, key, value):
        # Validate before saving
        if key == 'model' and value not in self.VALID_MODELS:
            raise ValueError(f"Invalid model: {value}")
        elif key == 'mic_index':
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid mic_index: {value}")
        elif key == 'language' and value not in self.VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {value}")
        elif key == 'sample_rate_mode' and value not in self.VALID_SAMPLE_RATE_MODES:
            raise ValueError(f"Invalid sample_rate_mode: {value}")
        
        # Get the old value for logging
        old_value = self.get(key)
        
        # Log the settings change
        logger.info(f"Setting changed: {key} = {value} (was: {old_value})")
                
        self.settings.setValue(key, value)
        self.settings.sync()