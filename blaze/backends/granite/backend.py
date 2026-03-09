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
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

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
            # Granite Speech uses AutoModelForSpeechSeq2Seq
            self._processor = AutoProcessor.from_pretrained(
                repo_id, cache_dir=self._cache_dir
            )
            self._model = AutoModelForSpeechSeq2Seq.from_pretrained(
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

            # Granite expects 16kHz audio
            sample_rate = 16000

            # Map language code
            lang_code = LANGUAGE_MAP.get(language, "en") if language else "en"

            # Prepare inputs for the model
            # Granite Speech uses AutoModelForSpeechSeq2Seq with raw audio
            inputs = self._processor(
                audio_np,  # Pass numpy array directly
                sampling_rate=sample_rate,
                return_tensors="pt",
                text=f"<|{lang_code}|>",  # Language token for ASR
            )

            # Move inputs to device
            if self._device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

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
        # Map from registry model_id to internal key if needed
        if model_id in GRANITE_MODELS:
            repo_id = GRANITE_MODELS[model_id]
        elif model_id == "granite-speech-3.3-2b":
            repo_id = "ibm-granite/granite-speech-3.3-2b"
        else:
            return False

        # Check HuggingFace cache with multiple methods
        try:
            from huggingface_hub import try_to_load_from_cache, scan_cache_dir
            import hashlib

            # Method 1: Check individual files
            for filename in [
                "model.safetensors",
                "pytorch_model.bin",
                "model.fp16.safetensors",
                "model-00001-of-00002.safetensors",
            ]:
                model_path = try_to_load_from_cache(repo_id, filename)
                if model_path is not None:
                    logger.debug(f"Found {filename} for {model_id}")
                    return True

            # Method 2: Check for config.json and verify model files in same dir
            config_path = try_to_load_from_cache(repo_id, "config.json")
            if config_path is not None:
                cache_dir = Path(config_path).parent
                # Look for any model weight files
                for pattern in ["*.safetensors", "*.bin", "*.pt"]:
                    if any(cache_dir.glob(pattern)):
                        logger.debug(f"Found model files in cache dir for {model_id}")
                        return True

            # Method 3: Scan entire cache for this repo
            try:
                cache_info = scan_cache_dir()
                for repo in cache_info.repos:
                    if repo.repo_id == repo_id:
                        logger.debug(f"Found repo in cache scan for {model_id}")
                        return True
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Error checking model cache: {e}")

        logger.debug(f"Model {model_id} not found in cache")
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
            if progress_callback:
                progress_callback(0)

            # Download the model
            snapshot_download(
                repo_id=repo_id,
                cache_dir=self._cache_dir,
                local_files_only=False,
            )

            logger.info(f"Successfully downloaded {model_id}")
            if progress_callback:
                progress_callback(100)
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
