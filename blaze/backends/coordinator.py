"""
Backend Coordinator

Manages the lifecycle of STT backends and handles switching between models.
This is the main entry point for the application to use different STT backends.
"""

import logging
from typing import Optional, Dict, Type, Callable

from blaze.backends.base import (
    BaseModelBackend,
    TranscriptionResult,
    ModelNotFoundError,
    ModelLoadError,
)
from blaze.backends.registry import ModelRegistry

logger = logging.getLogger(__name__)


class BackendCoordinator:
    """
    Coordinates between different STT backends.

    Handles:
    - Backend discovery and registration
    - Model loading/unloading
    - Transcription
    - Dependency management for optional backends
    """

    _backends: Dict[str, Type[BaseModelBackend]] = {}
    _current_backend: Optional[BaseModelBackend] = None
    _current_model_id: Optional[str] = None

    def __init__(self):
        self._discover_backends()

    def _discover_backends(self):
        """Discover and register available backends"""
        # Whisper backend (always available - core dependency)
        try:
            from blaze.backends.whisper import WhisperBackend

            self.register_backend("whisper", WhisperBackend)
            logger.info("✓ Whisper backend registered")
        except ImportError as e:
            logger.warning(f"Whisper backend not available: {e}")

        # Granite backend (optional - will prompt to install if needed)
        try:
            from blaze.backends.granite import GraniteBackend

            self.register_backend("granite", GraniteBackend)
            logger.info("✓ Granite backend registered")
        except ImportError:
            logger.info("Granite backend not available (optional - install to use)")

        # Liquid backend (optional)
        try:
            from blaze.backends.liquid import LiquidBackend

            self.register_backend("liquid", LiquidBackend)
            logger.info("✓ Liquid backend registered")
        except ImportError:
            logger.info("Liquid backend not available (optional - install to use)")

        # Qwen backend (optional - future)
        try:
            from blaze.backends.qwen import QwenBackend

            self.register_backend("qwen", QwenBackend)
            logger.info("✓ Qwen backend registered")
        except ImportError:
            logger.info("Qwen backend not available (optional - install to use)")

    @classmethod
    def register_backend(cls, name: str, backend_class: Type[BaseModelBackend]):
        """Register a backend class"""
        cls._backends[name] = backend_class
        logger.debug(f"Registered backend: {name}")

    def get_available_backends(self) -> list:
        """Get list of available backend names"""
        return list(self._backends.keys())

    def is_backend_available(self, backend_name: str) -> bool:
        """Check if a backend is available"""
        return backend_name in self._backends

    def load_model(self, model_id: str, device: str = "auto") -> bool:
        """
        Load a model by ID.

        Automatically switches backends if the model requires a different backend
        than the currently loaded one.

        Args:
            model_id: The model to load (e.g., 'whisper-tiny', 'granite-speech-3.3-2b')
            device: 'cpu', 'cuda', or 'auto'

        Returns:
            True if model loaded successfully

        Raises:
            ModelNotFoundError: If model is not downloaded
            ModelLoadError: If model fails to load
            ValueError: If backend is not available
        """
        # Get model info
        model_info = ModelRegistry.get_model(model_id)
        if not model_info:
            raise ValueError(f"Unknown model: {model_id}")

        backend_name = model_info.backend

        # Check if backend is available
        if backend_name not in self._backends:
            raise ValueError(
                f"Backend '{backend_name}' is not available. "
                f"Please install the required dependencies."
            )

        # Check if we need to switch backends
        if self._current_backend is not None:
            # Determine current backend type
            current_backend_name = None
            for name, backend_class in self._backends.items():
                if isinstance(self._current_backend, backend_class):
                    current_backend_name = name
                    break
            
            # Unload if wrong backend type
            if current_backend_name != backend_name:
                logger.info(
                    f"Switching from {current_backend_name or 'unknown'} to {backend_name} backend"
                )
                self.unload_model()

        # Create new backend instance if needed
        if self._current_backend is None:
            backend_class = self._backends[backend_name]
            self._current_backend = backend_class()

        # Load the model
        try:
            logger.info(f"Loading model {model_id} on device: {device}")
            self._current_backend.load(model_id, device)
            self._current_model_id = model_id
            logger.info(f"Successfully loaded model: {model_id}")
            return True
        except ModelNotFoundError:
            raise
        except Exception as e:
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def unload_model(self) -> None:
        """Unload the current model to free memory"""
        if self._current_backend is not None:
            logger.info(f"Unloading model: {self._current_model_id}")
            self._current_backend.unload()
            self._current_backend = None
            self._current_model_id = None

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio data using the currently loaded model.

        Args:
            audio_data: Raw audio bytes (typically 16kHz PCM)
            language: Optional language code (e.g., 'en', 'fr')

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            RuntimeError: If no model is loaded
        """
        if self._current_backend is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        return self._current_backend.transcribe(audio_data, language)

    def is_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model is downloaded locally.

        Args:
            model_id: Model to check

        Returns:
            True if model files exist locally
        """
        model_info = ModelRegistry.get_model(model_id)
        if not model_info:
            return False

        backend_name = model_info.backend
        if backend_name not in self._backends:
            # Can't check without backend, but assume not downloaded
            return False

        # Create temporary backend instance to check
        backend_class = self._backends[backend_name]
        backend = backend_class()
        return backend.is_model_downloaded(model_id)

    def download_model(
        self, model_id: str, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Download a model.

        Args:
            model_id: Model to download
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        model_info = ModelRegistry.get_model(model_id)
        if not model_info:
            logger.error(f"Unknown model: {model_id}")
            return False

        backend_name = model_info.backend
        if backend_name not in self._backends:
            logger.error(f"Backend '{backend_name}' not available for model {model_id}")
            return False

        backend_class = self._backends[backend_name]
        backend = backend_class()

        return backend.download_model(model_id, progress_callback)

    def delete_model(self, model_id: str) -> bool:
        """
        Delete a downloaded model.

        Args:
            model_id: Model to delete

        Returns:
            True if deletion succeeded
        """
        model_info = ModelRegistry.get_model(model_id)
        if not model_info:
            logger.error(f"Unknown model: {model_id}")
            return False

        backend_name = model_info.backend
        if backend_name not in self._backends:
            logger.error(f"Backend '{backend_name}' not available for model {model_id}")
            return False

        backend_class = self._backends[backend_name]
        backend = backend_class()

        return backend.delete_model(model_id)

    def get_current_model_id(self) -> Optional[str]:
        """Get the ID of the currently loaded model"""
        return self._current_model_id

    def get_current_backend_name(self) -> Optional[str]:
        """Get the name of the currently active backend"""
        if self._current_model_id:
            model_info = ModelRegistry.get_model(self._current_model_id)
            if model_info:
                return model_info.backend
        return None


# Singleton instance for application-wide use
_coordinator: Optional[BackendCoordinator] = None


def get_coordinator() -> BackendCoordinator:
    """Get the singleton BackendCoordinator instance"""
    global _coordinator
    if _coordinator is None:
        _coordinator = BackendCoordinator()
    return _coordinator
