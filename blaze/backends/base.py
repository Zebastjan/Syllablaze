"""
Base abstractions for STT backends.

Provides abstract base classes that all speech-to-text backends must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Hardware capability tiers for models"""

    ULTRA_LIGHT = "ultra_light"  # < 2GB RAM
    LIGHT = "light"  # 2-4GB RAM
    MEDIUM = "medium"  # 4-8GB RAM
    HEAVY = "heavy"  # 8GB+ RAM


@dataclass
class ModelCapability:
    """Metadata describing a model's capabilities and requirements"""

    model_id: str
    backend: str
    name: str
    description: str
    size_mb: int
    min_ram_gb: float
    recommended_ram_gb: float
    min_vram_gb: Optional[float]
    languages: List[str]
    tier: ModelTier
    license: str
    is_streaming: bool = False
    supports_word_timestamps: bool = False
    repo_id: Optional[str] = None  # HuggingFace repo ID for downloading


@dataclass
class TranscriptionResult:
    """Result from a transcription operation"""

    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    word_timestamps: Optional[List[Dict[str, Any]]] = None


class BaseModelBackend(ABC):
    """
    Abstract base class for STT model backends.

    All speech-to-text backends (Whisper, Granite, Liquid, Qwen) must implement
    this interface to be compatible with the application.
    """

    def __init__(self):
        self._loaded_model_id: Optional[str] = None
        self._device: str = "cpu"

    @abstractmethod
    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a model into memory.

        Args:
            model_id: The unique identifier for the model
            device: Device to load on ('cpu', 'cuda', or 'auto')
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload the current model from memory to free resources"""
        pass

    @abstractmethod
    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes (typically 16kHz PCM)
            language: Optional language code (e.g., 'en', 'fr').
                     Use None or 'auto' for auto-detection.

        Returns:
            TranscriptionResult with text and optional metadata
        """
        pass

    @abstractmethod
    def is_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model's files exist locally.

        Args:
            model_id: The model to check

        Returns:
            True if the model can be loaded without downloading
        """
        pass

    @abstractmethod
    def download_model(
        self, model_id: str, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Download a model from its source (e.g., HuggingFace).

        Args:
            model_id: The model to download
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        pass

    @abstractmethod
    def delete_model(self, model_id: str) -> bool:
        """
        Delete a downloaded model to free disk space.

        Args:
            model_id: The model to delete

        Returns:
            True if deletion succeeded
        """
        pass

    @property
    def loaded_model_id(self) -> Optional[str]:
        """Get the ID of the currently loaded model"""
        return self._loaded_model_id

    @property
    def device(self) -> str:
        """Get the device the model is loaded on"""
        return self._device


class BaseTranscriber(ABC):
    """
    Abstract base class for transcription workers.

    Handles the lifecycle of a transcription job, including threading
    and progress reporting.
    """

    @abstractmethod
    def start_transcription(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> Any:
        """
        Start an asynchronous transcription job.

        Args:
            audio_data: Raw audio bytes
            language: Optional language code

        Returns:
            A handle/object to track the job (implementation-specific)
        """
        pass

    @abstractmethod
    def cancel_transcription(self) -> None:
        """Cancel the current transcription job if running"""
        pass


class BackendError(Exception):
    """Base exception for backend-related errors"""

    pass


class ModelNotFoundError(BackendError):
    """Raised when a model is not found or not downloaded"""

    pass


class ModelLoadError(BackendError):
    """Raised when a model fails to load"""

    pass


class TranscriptionError(BackendError):
    """Raised when transcription fails"""

    pass
