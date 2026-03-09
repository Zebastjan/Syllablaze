"""
Qwen Backend

Speech-to-text using Alibaba's Qwen2-Audio models via transformers.

Dependencies:
    pip install git+https://github.com/huggingface/transformers
    pip install torchaudio librosa accelerate

Models:
    - qwen2-audio-7b-instruct: 7B parameters, multilingual ASR

Supported languages:
    - Chinese (zh), English (en), Japanese (ja), Korean (ko)
    - Arabic (ar), French (fr), German (de), Spanish (es)
    - Italian (it), Portuguese (pt), Russian (ru), and more
"""

# Check dependencies
try:
    import transformers
    import torchaudio
    import librosa
except ImportError as e:
    raise ImportError(
        f"Qwen backend requires transformers, torchaudio, and librosa: {e}. "
        "Install with: pip install git+https://github.com/huggingface/transformers "
        "torchaudio librosa accelerate"
    )

from blaze.backends.qwen.backend import QwenBackend

__all__ = ["QwenBackend"]
