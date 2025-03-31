from PyQt6.QtCore import QSettings
from blaze.constants import (
    APP_NAME, VALID_LANGUAGES,
    SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE, DEFAULT_SAMPLE_RATE_MODE,
    DEFAULT_COMPUTE_TYPE, DEFAULT_DEVICE, DEFAULT_BEAM_SIZE, DEFAULT_VAD_FILTER, DEFAULT_WORD_TIMESTAMPS
)
import logging

logger = logging.getLogger(__name__)

class Settings:
    # List of valid language codes for Whisper
    VALID_LANGUAGES = VALID_LANGUAGES
    # Valid sample rate modes
    VALID_SAMPLE_RATE_MODES = [SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE]
    # Valid compute types for Faster Whisper
    VALID_COMPUTE_TYPES = ['float32', 'float16', 'int8']
    # Valid devices for Faster Whisper
    VALID_DEVICES = ['cpu', 'cuda']
    
    def __init__(self):
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.init_default_settings()
        
    def init_default_settings(self):
        """Initialize default settings if they don't exist"""
        # Faster Whisper settings
        if self.settings.value('compute_type') is None:
            self.settings.setValue('compute_type', DEFAULT_COMPUTE_TYPE)
        if self.settings.value('device') is None:
            self.settings.setValue('device', DEFAULT_DEVICE)
        if self.settings.value('beam_size') is None:
            self.settings.setValue('beam_size', DEFAULT_BEAM_SIZE)
        if self.settings.value('vad_filter') is None:
            self.settings.setValue('vad_filter', DEFAULT_VAD_FILTER)
        if self.settings.value('word_timestamps') is None:
            self.settings.setValue('word_timestamps', DEFAULT_WORD_TIMESTAMPS)
        
    def get(self, key, default=None):
        value = self.settings.value(key, default)
        
        # Validate specific settings
        if key == 'model':
            # We'll validate models in the model manager
            pass
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
        elif key == 'compute_type' and value not in self.VALID_COMPUTE_TYPES:
            logger.warning(f"Invalid compute_type in settings: {value}, using default: {DEFAULT_COMPUTE_TYPE}")
            return DEFAULT_COMPUTE_TYPE
        elif key == 'device' and value not in self.VALID_DEVICES:
            logger.warning(f"Invalid device in settings: {value}, using default: {DEFAULT_DEVICE}")
            return DEFAULT_DEVICE
        elif key == 'beam_size':
            try:
                beam_size = int(value)
                if beam_size < 1 or beam_size > 10:
                    logger.warning(f"Invalid beam_size in settings: {value}, using default: {DEFAULT_BEAM_SIZE}")
                    return DEFAULT_BEAM_SIZE
                return beam_size
            except (ValueError, TypeError):
                logger.warning(f"Invalid beam_size in settings: {value}, using default: {DEFAULT_BEAM_SIZE}")
                return DEFAULT_BEAM_SIZE
        elif key == 'vad_filter':
            if isinstance(value, str):
                return value.lower() in ['true', '1', 'yes']
            return bool(value)
        elif key == 'word_timestamps':
            if isinstance(value, str):
                return value.lower() in ['true', '1', 'yes']
            return bool(value)
        
        # Log the settings access for important settings
        if key in ['model', 'language', 'sample_rate_mode', 'compute_type', 'device', 'beam_size', 'vad_filter', 'word_timestamps']:
            logger.info(f"Setting accessed: {key} = {value}")
                
        return value
        
    def set(self, key, value):
        # Validate before saving
        if key == 'model':
            # We'll validate models in the model manager
            pass
        elif key == 'mic_index':
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid mic_index: {value}")
        elif key == 'language' and value not in self.VALID_LANGUAGES:
            raise ValueError(f"Invalid language: {value}")
        elif key == 'sample_rate_mode' and value not in self.VALID_SAMPLE_RATE_MODES:
            raise ValueError(f"Invalid sample_rate_mode: {value}")
        elif key == 'compute_type' and value not in self.VALID_COMPUTE_TYPES:
            raise ValueError(f"Invalid compute_type: {value}")
        elif key == 'device' and value not in self.VALID_DEVICES:
            raise ValueError(f"Invalid device: {value}")
        elif key == 'beam_size':
            try:
                beam_size = int(value)
                if beam_size < 1 or beam_size > 10:
                    raise ValueError(f"Invalid beam_size: {value}. Must be between 1 and 10.")
                value = beam_size
            except (ValueError, TypeError):
                raise ValueError(f"Invalid beam_size: {value}")
        elif key == 'vad_filter':
            value = bool(value)
        elif key == 'word_timestamps':
            value = bool(value)
        
        # Get the old value for logging
        old_value = self.get(key)
        
        # Log the settings change
        logger.info(f"Setting changed: {key} = {value} (was: {old_value})")
                
        self.settings.setValue(key, value)
        self.settings.sync()
        
    def save(self):
        """Save settings to disk"""
        self.settings.sync()