"""
Granite Backend

IBM Granite Speech backend for speech-to-text.
"""

# Check for required dependencies
try:
    import transformers
    import torchaudio
    import peft
    import soundfile
except ImportError as e:
    raise ImportError(
        f"Granite backend requires transformers, torchaudio, peft, and soundfile: {e}"
    )

# Import the backend class
from blaze.backends.granite.backend import GraniteBackend

__all__ = ["GraniteBackend"]
