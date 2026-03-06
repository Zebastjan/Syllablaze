"""
IBM Granite Speech Backend

Speech-to-text using IBM's Granite Speech models.

Dependencies:
    pip install transformers>=4.30.0 torchaudio peft soundfile

Model info:
    - Granite Speech 3.3-2B: 2B parameters
    - Supports: EN, FR, DE, ES, PT (ASR)
    - Supports: EN->JA, EN->ZH (translation)
    - License: Apache-2.0
"""

import os
import io
import wave
import logging
from typing import Optional, Callable
from pathlib import Path

import numpy as np
import torch
import torchaudio

from blaze.backends.base import (
    BaseModelBackend,
    TranscriptionResult,
    ModelNotFoundError,
    ModelLoadError,
    TranscriptionError,
)
from blaze.backends.registry import ModelRegistry

logger = logging.getLogger(__name__)

# Model repo IDs
GRANITE_MODELS = {
    "granite-speech-3.3-2b": "ibm-granite/granite-speech-3.3-2b",
}

# Language code mapping (standard to Granite format)
LANGUAGE_MAP = {
    "en": "en",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "pt": "pt",
    "ja": "ja",  # For translation target
    "zh": "zh",  # For translation target
}


class GraniteBackend(BaseModelBackend):
    """
        IBM Granite Speech backend for speech-to-text.

    n    This backend uses transformers and peft to run inference
        on IBM's Granite Speech models.
    """

    def __init__(self):
        super().__init__()
        self._processor: Optional = None
        self._model: Optional = None
        self._device: str = "cpu"
        self._cache_dir = Path.home() / ".cache" / "syllablaze" / "granite"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a Granite Speech model.

        Args:
            model_id: Model ID (e.g., 'granite-speech-3.3-2b')
            device: 'cpu', 'cuda', or 'auto'
        """
        from transformers import AutoModel, AutoProcessor

        # Validate model ID
        if model_id not in GRANITE_MODELS:
            raise ModelNotFoundError(f"Unknown Granite model: {model_id}")

        repo_id = GRANITE_MODELS[model_id]

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device = device

        try:
            logger.info(f"Loading Granite model: {model_id} from {repo_id}")
            logger.info(f"Device: {device}")

            # Load processor and model
            # Granite Speech uses AutoModel and AutoProcessor from transformers
            self._processor = AutoProcessor.from_pretrained(
                repo_id, cache_dir=self._cache_dir
            )
            self._model = AutoModel.from_pretrained(
                repo_id,
                cache_dir=self._cache_dir,
                trust_remote_code=True,  # Required for Granite models
            )

            # Move to device
            if device == "cuda" and torch.cuda.is_available():
                self._model = self._model.cuda()

            self._model.eval()

            self._loaded_model_id = model_id
            logger.info(f"Successfully loaded {model_id}")

        except Exception as e:
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def unload(self) -> None:
        """Unload the model to free memory"""
        if self._model is not None:
            logger.info(f"Unloading Granite model: {self._loaded_model_id}")
            del self._model
            del self._processor
            self._model = None
            self._processor = None
            self._loaded_model_id = None

            import gc

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio using Granite Speech.

        Args:
            audio_data: Raw audio bytes (16kHz PCM, mono)
            language: Optional language code (e.g., 'en', 'fr')
                     None defaults to auto-detection or English

        Returns:
            TranscriptionResult with text
        """
        if self._model is None or self._processor is None:
            raise TranscriptionError("Model not loaded. Call load() first.")

        try:
            # Convert bytes to numpy array (16kHz PCM input)
            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Convert to torch tensor
            wav = torch.from_numpy(audio_np)

            # Ensure correct shape [samples]
            if wav.dim() > 1:
                wav = wav.squeeze()

            # Granite expects 16kHz audio, so verify/resample if needed
            # For now assume input is 16kHz
            sample_rate = 16000

            # Move to device
            if self._device == "cuda" and torch.cuda.is_available():
                wav = wav.cuda()

            # Map language code
            lang_code = LANGUAGE_MAP.get(language, "en") if language else "en"

            # Prepare inputs for the model
            # Granite Speech uses a specific input format
            inputs = self._processor(
                audio=wav.cpu().numpy(),  # Processor expects numpy
                sampling_rate=sample_rate,
                return_tensors="pt",
                text=f"<|{lang_code}|>",  # Language token for ASR
            )

            # Move inputs to device
            if self._device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            # Generate transcription
            with torch.no_grad():
                outputs = self._model.generate(**inputs, max_new_tokens=256)

            # Decode the output
            transcription = self._processor.batch_decode(
                outputs, skip_special_tokens=True
            )[0]

            return TranscriptionResult(
                text=transcription.strip(),
                language=language or "en",
                confidence=None,  # Granite doesn't provide confidence scores directly
            )

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if model is downloaded in HuggingFace cache"""
        if model_id not in GRANITE_MODELS:
            return False

        repo_id = GRANITE_MODELS[model_id]

        # Check HuggingFace cache
        try:
            from huggingface_hub import try_to_load_from_cache

            # Try to find model files in cache
            model_path = try_to_load_from_cache(repo_id, "model.safetensors")
            if model_path is not None:
                return True

            # Try pytorch format
            model_path = try_to_load_from_cache(repo_id, "pytorch_model.bin")
            if model_path is not None:
                return True

            # Check for config.json (indicates partial download)
            config_path = try_to_load_from_cache(repo_id, "config.json")
            if config_path is not None:
                # If we have config, check if model files exist in cache dir
                cache_dir = Path(config_path).parent
                has_model = any(cache_dir.glob("*.safetensors")) or any(
                    cache_dir.glob("*.bin")
                )
                return has_model

        except Exception as e:
            logger.debug(f"Error checking model cache: {e}")

        return False

    def download_model(
        self, model_id: str, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Download a Granite model from HuggingFace.

        Args:
            model_id: Model to download
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        from huggingface_hub import snapshot_download

        if model_id not in GRANITE_MODELS:
            logger.error(f"Unknown Granite model: {model_id}")
            return False

        repo_id = GRANITE_MODELS[model_id]

        try:
            logger.info(f"Downloading Granite model: {repo_id}")

            # Download with progress tracking
            def hf_progress_callback(info):
                if progress_callback and hasattr(info, "completed"):
                    progress = (
                        int((info.completed / info.total) * 100) if info.total else 0
                    )
                    progress_callback(progress)

            snapshot_download(
                repo_id=repo_id,
                cache_dir=self._cache_dir,
                local_files_only=False,
            )

            logger.info(f"Successfully downloaded {model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {model_id}: {e}")
            return False

    def delete_model(self, model_id: str) -> bool:
        """
        Delete a downloaded model.

        Args:
            model_id: Model to delete

        Returns:
            True if deletion succeeded
        """
        import shutil

        if model_id not in GRANITE_MODELS:
            return False

        try:
            # Unload if currently loaded
            if self._loaded_model_id == model_id:
                self.unload()

            repo_id = GRANITE_MODELS[model_id]

            # Find cache directory
            try:
                from huggingface_hub import try_to_load_from_cache

                config_path = try_to_load_from_cache(repo_id, "config.json")
                if config_path:
                    cache_dir = Path(config_path).parent
                    if cache_dir.exists():
                        logger.info(f"Deleting model cache: {cache_dir}")
                        shutil.rmtree(cache_dir)
                        return True
            except Exception as e:
                logger.warning(f"Could not find cache dir for deletion: {e}")

            return False

        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return False
