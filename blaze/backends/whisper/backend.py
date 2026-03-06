"""
Whisper Backend Implementation

Adapter that wraps the existing Whisper model infrastructure to implement
the BaseModelBackend interface.
"""

import os
import io
import wave
import logging
from typing import Optional, Callable

from blaze.backends.base import (
    BaseModelBackend,
    TranscriptionResult,
    ModelNotFoundError,
    ModelLoadError,
    TranscriptionError,
)
from blaze.backends.registry import ModelRegistry
from blaze.models.manager import WhisperModelManager
from blaze.models.paths import ModelPaths

logger = logging.getLogger(__name__)


class WhisperBackend(BaseModelBackend):
    """
    Whisper STT backend using faster-whisper.

    Wraps the existing WhisperModelManager to provide the new
    BaseModelBackend interface.
    """

    def __init__(self):
        super().__init__()
        self._manager: Optional[WhisperModelManager] = None
        self._model: Optional = None  # faster_whisper.WhisperModel instance

    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a Whisper model.

        Args:
            model_id: Model ID (e.g., 'whisper-tiny', 'whisper-large-v3')
            device: 'cpu', 'cuda', or 'auto'
        """
        # Convert new model_id format to old format if needed
        # whisper-tiny -> tiny
        old_model_name = self._convert_model_id(model_id)

        # Check if model is downloaded
        if not self.is_model_downloaded(model_id):
            raise ModelNotFoundError(
                f"Model {model_id} is not downloaded. Please download it first."
            )

        # Import faster_whisper here to avoid loading at module level
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ModelLoadError("faster-whisper is not installed. Please install it.")

        # Determine device and compute type
        if device == "auto":
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"

        # Map device to faster-whisper format
        device_type = device  # 'cpu' or 'cuda'
        device_index = 0 if device == "cuda" else "auto"

        # Determine compute type based on device
        if device == "cuda":
            compute_type = "float16"  # Use float16 on GPU for speed
        else:
            compute_type = "int8"  # Use int8 on CPU for memory efficiency

        try:
            # Get model path
            model_path = self._get_model_path(old_model_name)

            logger.info(f"Loading Whisper model: {model_id} from {model_path}")
            logger.info(f"Device: {device_type}, Compute type: {compute_type}")

            self._model = WhisperModel(
                model_path,
                device=device_type,
                device_index=device_index if device == "cuda" else 0,
                compute_type=compute_type,
                cpu_threads=4 if device == "cpu" else 0,
            )

            self._loaded_model_id = model_id
            self._device = device

            logger.info(f"Successfully loaded {model_id}")

        except Exception as e:
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def unload(self) -> None:
        """Unload the current model to free memory"""
        if self._model is not None:
            logger.info(f"Unloading model: {self._loaded_model_id}")
            # Delete the model reference to free memory
            del self._model
            self._model = None
            self._loaded_model_id = None

            # Force garbage collection
            import gc

            gc.collect()

            # Clear CUDA cache if using GPU
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio data using the loaded Whisper model.

        Args:
            audio_data: Raw audio bytes (16kHz, 16-bit PCM)
            language: Optional language code (e.g., 'en', 'fr')

        Returns:
            TranscriptionResult with text and metadata
        """
        if self._model is None:
            raise TranscriptionError("No model loaded. Call load() first.")

        try:
            # Convert bytes to numpy array
            import numpy as np

            # audio_data should be 16kHz 16-bit PCM
            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Handle language parameter
            if language == "auto" or language is None:
                language = None  # Whisper will auto-detect

            # Transcribe
            segments, info = self._model.transcribe(
                audio_np,
                language=language,
                task="transcribe",
                beam_size=5,
                best_of=5,
                condition_on_previous_text=True,
            )

            # Collect all segments into full text
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            full_text = " ".join(text_parts).strip()

            return TranscriptionResult(
                text=full_text,
                language=info.language if info else None,
                confidence=None,  # faster-whisper doesn't provide confidence
            )

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if a model is downloaded locally"""
        old_model_name = self._convert_model_id(model_id)

        # Use ModelUtils to check (reuses existing logic)
        from blaze.models.paths import ModelUtils

        return ModelUtils.is_model_downloaded(old_model_name)

    def download_model(
        self, model_id: str, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Download a Whisper model from HuggingFace.

        Args:
            model_id: Model to download
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        old_model_name = self._convert_model_id(model_id)

        try:
            from huggingface_hub import snapshot_download

            # Get the model info to find the repo_id
            model_info = ModelRegistry.get_model(model_id)
            if not model_info:
                logger.error(f"Unknown model: {model_id}")
                return False

            repo_id = model_info.repo_id
            if not repo_id:
                logger.error(f"No repo_id for model: {model_id}")
                return False

            logger.info(f"Downloading {model_id} from {repo_id}")

            # Download using snapshot_download
            models_dir = ModelPaths.get_models_dir()
            local_dir = os.path.join(
                models_dir, f"models--{repo_id.replace('/', '--')}"
            )

            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
            )

            logger.info(f"Successfully downloaded {model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            return False

    def delete_model(self, model_id: str) -> bool:
        """
        Delete a downloaded model.

        Args:
            model_id: Model to delete

        Returns:
            True if deletion succeeded
        """
        old_model_name = self._convert_model_id(model_id)

        try:
            # Can't delete currently loaded model
            if self._loaded_model_id == model_id:
                self.unload()

            from blaze.models.paths import ModelPaths
            import shutil

            # Get the model directory
            model_dir = ModelPaths.get_faster_whisper_dir(old_model_name)

            if os.path.exists(model_dir):
                logger.info(f"Deleting model directory: {model_dir}")
                shutil.rmtree(model_dir)
                return True
            else:
                # Try alternative paths
                alt_dir = ModelPaths.get_faster_distil_dir(old_model_name)
                if os.path.exists(alt_dir):
                    logger.info(f"Deleting model directory: {alt_dir}")
                    shutil.rmtree(alt_dir)
                    return True

                logger.warning(f"Model directory not found: {model_dir}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return False

    def _convert_model_id(self, model_id: str) -> str:
        """
        Convert new model_id format to old Whisper format.

        Examples:
            whisper-tiny -> tiny
            whisper-distil-small.en -> distil-small.en
        """
        if model_id.startswith("whisper-"):
            return model_id[8:]  # Remove "whisper-" prefix
        return model_id

    def _get_model_path(self, old_model_name: str) -> str:
        """Get the local path for a model in old naming format"""
        from blaze.models.paths import ModelPaths

        # Try faster-whisper path first
        path = ModelPaths.get_faster_whisper_dir(old_model_name)
        if os.path.exists(path):
            return path

        # Try distil-whisper path
        path = ModelPaths.get_faster_distil_dir(old_model_name)
        if os.path.exists(path):
            return path

        # Return the faster-whisper path even if it doesn't exist
        # (will fail with a better error message later)
        return ModelPaths.get_faster_whisper_dir(old_model_name)
