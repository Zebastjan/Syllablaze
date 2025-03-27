# Import constants from parent directory
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import constants from parent
from constants import APP_VERSION, APP_NAME, ORG_NAME, DEFAULT_WHISPER_MODEL, VALID_LANGUAGES

# Re-export all constants
__all__ = ['APP_VERSION', 'APP_NAME', 'ORG_NAME', 'DEFAULT_WHISPER_MODEL', 'VALID_LANGUAGES']