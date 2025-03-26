"""
Constants for the Syllablaze application.
"""

# Application name
APP_NAME = "Syllablaze"

# Organization name
ORG_NAME = "KDE"

# Default whisper model
DEFAULT_WHISPER_MODEL = "tiny"

# Valid whisper models
VALID_WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large', 'turbo']

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