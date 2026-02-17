from PyQt6.QtCore import QSettings
from blaze.constants import (
    APP_NAME, VALID_LANGUAGES,
    SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE, DEFAULT_SAMPLE_RATE_MODE,
    DEFAULT_COMPUTE_TYPE, DEFAULT_DEVICE, DEFAULT_BEAM_SIZE, DEFAULT_VAD_FILTER, DEFAULT_WORD_TIMESTAMPS,
    DEFAULT_SHORTCUT,
    APPLET_MODE_OFF, APPLET_MODE_PERSISTENT, APPLET_MODE_POPUP, DEFAULT_APPLET_MODE,
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
    # Valid applet modes for recording dialog
    VALID_APPLET_MODES = [APPLET_MODE_OFF, APPLET_MODE_PERSISTENT, APPLET_MODE_POPUP]
    
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

        # UI settings - recording dialog
        if self.settings.value('show_recording_dialog') is None:
            self.settings.setValue('show_recording_dialog', True)
        if self.settings.value('recording_dialog_always_on_top') is None:
            self.settings.setValue('recording_dialog_always_on_top', True)
        if self.settings.value('recording_dialog_size') is None:
            self.settings.setValue('recording_dialog_size', 200)
        if self.settings.value('recording_dialog_x') is None:
            self.settings.setValue('recording_dialog_x', None)  # None = let window manager decide
        if self.settings.value('recording_dialog_y') is None:
            self.settings.setValue('recording_dialog_y', None)

        # UI settings - progress window
        if self.settings.value('show_progress_window') is None:
            self.settings.setValue('show_progress_window', True)
        if self.settings.value('progress_window_always_on_top') is None:
            self.settings.setValue('progress_window_always_on_top', True)

        # Applet mode for recording dialog behavior
        if self.settings.value('applet_mode') is None:
            self.settings.setValue('applet_mode', DEFAULT_APPLET_MODE)
        
    def get(self, key, default=None):
        """Get a setting value with proper type conversion"""
        value = self.settings.value(key, default)

        # Handle None/null values
        if value is None:
            return default

        # Boolean settings - convert strings to booleans
        boolean_settings = [
            'vad_filter',
            'word_timestamps',
            'show_recording_dialog',
            'recording_dialog_always_on_top',
            'show_progress_window',
            'progress_window_always_on_top',
        ]

        if key in boolean_settings:
            if isinstance(value, str):
                return value.lower() in ['true', '1', 'yes']
            return bool(value)

        # Integer settings - ensure proper conversion
        integer_settings = [
            'beam_size',
            'mic_index',
            'recording_dialog_size',
            'recording_dialog_x',
            'recording_dialog_y',
        ]

        if key in integer_settings:
            if value is None:
                return default
            # Handle QSettings @Invalid() - when stored None is read, it might be string or QVariant
            if isinstance(value, str) and (value == '' or '@Invalid' in value):
                logger.debug(f"Setting {key} has invalid/empty value: {value!r}, returning default: {default}")
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                if key == 'beam_size':
                    logger.warning(f"Invalid beam_size in settings: {value!r}, using default: {DEFAULT_BEAM_SIZE}")
                    return DEFAULT_BEAM_SIZE
                elif key == 'mic_index':
                    logger.warning(f"Invalid mic_index in settings: {value!r}, using default: {default}")
                    return default
                logger.debug(f"Cannot convert {key}={value!r} to int, returning default: {default}")
                return default

        # Validate specific settings
        if key == 'model':
            # We'll validate models in the model manager
            pass
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
        elif key == 'applet_mode' and value not in self.VALID_APPLET_MODES:
            logger.warning(f"Invalid applet_mode in settings: {value}, using default: {DEFAULT_APPLET_MODE}")
            return DEFAULT_APPLET_MODE
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
        elif key == 'shortcut':
            if not value or not isinstance(value, str) or not value.strip():
                return DEFAULT_SHORTCUT
            return value

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
        elif key == 'applet_mode' and value not in self.VALID_APPLET_MODES:
            raise ValueError(f"Invalid applet_mode: {value}")
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
        elif key == 'shortcut':
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid shortcut: {value}")
            if '+' not in value and len(value) > 1:
                raise ValueError(f"Invalid shortcut format: {value}. Use format like 'Alt+Space'")

        # Get the old value for logging
        old_value = self.get(key)

        # Log the settings change with repr() for better debugging
        logger.info(f"Setting changed: {key} = {value!r} (was: {old_value!r})")

        self.settings.setValue(key, value)
        self.settings.sync()  # Force write to disk
        
    def save(self):
        """Save settings to disk"""
        self.settings.sync()