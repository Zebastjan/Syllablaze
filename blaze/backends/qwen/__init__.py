"""
Qwen Backend (Placeholder)

This backend will be implemented when Qwen ASR dependencies are installed.
For now, it raises ImportError to indicate the backend is not available.
"""

# This module will fail to import if transformers and torchaudio are not installed
# The BackendCoordinator will catch this and mark the backend as unavailable

try:
    import transformers
    import torchaudio
except ImportError as e:
    raise ImportError(f"Qwen backend requires transformers and torchaudio: {e}")

# If we get here, dependencies are available
from blaze.backends.base import (
    BaseModelBackend,
    TranscriptionResult,
    ModelNotFoundError,
)


class QwenBackend(BaseModelBackend):
    """
    Qwen ASR backend.

    Requires: transformers, torchaudio
    """

    def load(self, model_id: str, device: str = "auto") -> None:
        raise NotImplementedError("Qwen backend not yet implemented")

    def unload(self) -> None:
        pass

    def transcribe(
        self, audio_data: bytes, language: str = None
    ) -> TranscriptionResult:
        raise NotImplementedError("Qwen backend not yet implemented")

    def is_model_downloaded(self, model_id: str) -> bool:
        return False

    def download_model(self, model_id: str, progress_callback: callable = None) -> bool:
        raise NotImplementedError("Qwen backend not yet implemented")

    def delete_model(self, model_id: str) -> bool:
        return False
