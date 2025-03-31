"""
Constants for the Syllablaze application.
"""
import os


# Application name
APP_NAME = "Syllablaze"

# Application version
APP_VERSION = "0.4 beta"

# Organization name
ORG_NAME = "KDE"

# GitHub repository URL
GITHUB_REPO_URL = "https://github.com/PabloVitasso/Syllablaze"

# Default whisper model
DEFAULT_WHISPER_MODEL = "tiny"

# No model information needed - using whisper._MODELS directly

# Sample rate constants
WHISPER_SAMPLE_RATE = 16000  # 16kHz for Whisper
SAMPLE_RATE_MODE_WHISPER = "whisper"  # Use 16kHz optimized for Whisper
SAMPLE_RATE_MODE_DEVICE = "device"    # Use device's default sample rate
DEFAULT_SAMPLE_RATE_MODE = SAMPLE_RATE_MODE_WHISPER  # Default to Whisper-optimized

# Faster Whisper settings
DEFAULT_COMPUTE_TYPE = 'float32'  # or 'float16', 'int8'
DEFAULT_DEVICE = 'cpu'  # or 'cuda'
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True
DEFAULT_WORD_TIMESTAMPS = False

# Valid language codes for Whisper
VALID_LANGUAGES = {
    'auto': 'Auto-detect',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'nl': 'Dutch',
    'pl': 'Polish',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'ru': 'Russian',
    # Add more languages as needed
}

# Lock file configuration - path where the application lock file will be stored
# This is just the path string, not the actual file handle
LOCK_FILE_PATH = os.path.expanduser("~/.cache/syllablaze/syllablaze.lock")