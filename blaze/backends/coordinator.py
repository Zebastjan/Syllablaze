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

    def __init__(self):
        # Instance-level state for proper backend isolation
        self._backends: Dict[str, Type[BaseModelBackend]] = {}
        self._current_backend: Optional[BaseModelBackend] = None
        self._current_model_id: Optional[str] = None
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

    def register_backend(self, name: str, backend_class: Type[BaseModelBackend]):
        """Register a backend class"""
        self._backends[name] = backend_class
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

    def load_model_atomic(self, model_id: str, device: str = "auto") -> bool:
        """
        Load a model with GPU memory cleanup and error handling.

        Unloads the current model first to free GPU memory, then loads the new model.
        If the new model fails to load, the system will attempt to fallback to a
        known-good model (handled by the transcriber layer).

        Args:
            model_id: The model to load
            device: 'cpu', 'cuda', or 'auto'

        Returns:
            True if model loaded successfully

        Raises:
            ModelNotFoundError: If model is not downloaded
            ModelLoadError: If model fails to load
            ValueError: If backend is not available
        """
        # Save current state for logging
        old_backend = self._current_backend
        old_model_id = self._current_model_id

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

        # Determine current backend type
        current_backend_name = None
        if old_backend is not None:
            for name, backend_class in self._backends.items():
                if isinstance(old_backend, backend_class):
                    current_backend_name = name
                    break

        needs_backend_switch = (current_backend_name != backend_name)

        logger.info(
            f"Loading model: {model_id} on {device} "
            f"(backend: {backend_name}, switch: {needs_backend_switch})"
        )

        # CRITICAL: Unload old model FIRST to free GPU memory
        if old_backend is not None:
            try:
                old_device = getattr(old_backend, '_device', 'unknown')
                logger.info(
                    f"Unloading old model: {old_model_id} "
                    f"(backend: {current_backend_name}, device: {old_device})"
                )
                old_backend.unload()

                # Clear coordinator state immediately
                self._current_backend = None
                self._current_model_id = None

                logger.debug("Old model unloaded successfully")
            except Exception as e:
                logger.warning(f"Error unloading old model (continuing anyway): {e}")

        try:
            # Create new backend instance
            backend_class = self._backends[backend_name]
            new_backend = backend_class()

            # Force GPU memory cleanup before loading new model
            # This ensures maximum available memory for the new model load
            if device in ("cuda", "auto"):
                try:
                    import gc
                    import torch

                    logger.debug("Forcing GPU memory cleanup before model load")

                    # Force Python garbage collection
                    gc.collect()

                    # Clear PyTorch CUDA cache if available
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()

                        # Log memory stats for debugging
                        if torch.cuda.device_count() > 0:
                            allocated = torch.cuda.memory_allocated(0) / 1024**3
                            reserved = torch.cuda.memory_reserved(0) / 1024**3
                            logger.debug(
                                f"GPU memory after cleanup: "
                                f"{allocated:.2f}GB allocated, {reserved:.2f}GB reserved"
                            )

                except ImportError:
                    logger.debug("PyTorch not available, skipping GPU cleanup")
                except Exception as e:
                    logger.warning(f"GPU cleanup failed (non-critical): {e}")

            # Load the new model
            new_backend.load(model_id, device)

            # Success! Commit new state
            self._current_backend = new_backend
            self._current_model_id = model_id

            logger.info(f"✓ Model loaded successfully: {model_id}")
            return True

        except Exception as e:
            # Failure: Old model already unloaded, new model failed
            # System is now in "no model loaded" state
            # The fallback mechanism at the transcriber layer will handle recovery
            logger.error(
                f"✗ Model load failed for {model_id} "
                f"(previous model {old_model_id} was unloaded): {e}"
            )

            # Ensure coordinator state is cleared
            self._current_backend = None
            self._current_model_id = None

            # Re-raise with clear context
            raise ModelLoadError(
                f"Failed to load model {model_id}: {e}. "
                f"Previous model ({old_model_id}) was unloaded. "
                f"System will attempt to load a fallback model."
            )

    def unload_model(self) -> None:
        """Unload the current model to free memory"""
        if self._current_backend is not None:
            backend_name = self.get_current_backend_name()
            device = getattr(self._current_backend, '_device', 'unknown')

            logger.info(
                f"Unloading model: {self._current_model_id} | "
                f"Backend: {backend_name} | Device: {device}"
            )

            self._current_backend.unload()
            self._current_backend = None
            self._current_model_id = None

            logger.debug("Model unloaded, coordinator state cleared")

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

    def _validate_state(self) -> None:
        """
        Validate coordinator state consistency.

        Raises:
            AssertionError: If state is inconsistent
        """
        # Backend and model_id must both be set or both be None
        assert (self._current_backend is None) == (
            self._current_model_id is None
        ), (
            f"State inconsistency: backend={'set' if self._current_backend else 'None'}, "
            f"model_id={self._current_model_id}"
        )

        # If both are set, backend's loaded model must match coordinator's model
        if self._current_backend and self._current_model_id:
            backend_model = self._current_backend.loaded_model_id
            assert backend_model == self._current_model_id, (
                f"Backend model mismatch: "
                f"backend has '{backend_model}', coordinator has '{self._current_model_id}'"
            )


# Singleton instance for application-wide use
_coordinator: Optional[BackendCoordinator] = None


def get_coordinator() -> BackendCoordinator:
    """Get the singleton BackendCoordinator instance"""
    global _coordinator
    if _coordinator is None:
        _coordinator = BackendCoordinator()
    return _coordinator
