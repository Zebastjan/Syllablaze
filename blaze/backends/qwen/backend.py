"""
Qwen2-Audio Backend Implementation

Speech-to-text using Alibaba's Qwen2-Audio models via transformers.

Dependencies:
    pip install git+https://github.com/huggingface/transformers
    pip install torchaudio librosa accelerate

Model info:
    - Qwen2-Audio-7B-Instruct: 7B parameters, multilingual ASR
    - Supports Chinese, English, Japanese, Korean, Arabic, and more
    - Input: 16kHz audio (processor handles resampling)
    - License: Apache-2.0
"""

import os
import io
import logging
from typing import Optional, Callable
from pathlib import Path

import numpy as np
import torch

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
QWEN_MODELS = {
    "qwen2-audio-7b-instruct": "Qwen/Qwen2-Audio-7B-Instruct",
}


class QwenBackend(BaseModelBackend):
    """
    Qwen2-Audio backend for speech-to-text.

    This backend uses the transformers library to run inference
    on Qwen's audio-language models.
    """

    def __init__(self):
        super().__init__()
        self._processor: Optional = None
        self._model: Optional = None
        self._device: str = "cpu"
        self._loaded_model_id: Optional[str] = None

    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a Qwen Audio model.

        Args:
            model_id: Model ID (e.g., 'qwen2-audio-7b-instruct')
            device: 'cpu', 'cuda', or 'auto'
        """
        from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

        # Validate model ID
        if model_id not in QWEN_MODELS:
            raise ModelNotFoundError(f"Unknown Qwen model: {model_id}")

        repo_id = QWEN_MODELS[model_id]

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device = device

        try:
            logger.info(f"Loading Qwen model: {model_id} from {repo_id}")
            logger.info(f"Device: {device}")

            # Load processor and model
            self._processor = AutoProcessor.from_pretrained(repo_id)
            self._model = Qwen2AudioForConditionalGeneration.from_pretrained(
                repo_id,
                device_map="auto" if device == "cuda" else None,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            )

            if device == "cpu":
                self._model = self._model.to("cpu")

            self._model.eval()

            self._loaded_model_id = model_id
            logger.info(f"Successfully loaded {model_id}")

        except Exception as e:
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def unload(self) -> None:
        """Unload the model to free memory"""
        if self._model is not None:
            logger.info(f"Unloading Qwen model: {self._loaded_model_id}")
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
        Transcribe audio using Qwen2-Audio.

        Args:
            audio_data: Raw audio bytes (16kHz PCM, mono)
            language: Optional language hint (e.g., 'en', 'zh')

        Returns:
            TranscriptionResult with text
        """
        if self._model is None or self._processor is None:
            raise TranscriptionError("Model not loaded. Call load() first.")

        try:
            # Convert bytes to numpy array (assuming 16kHz PCM input)
            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Build conversation for transcription
            # Use the language hint in the prompt if provided
            if language and language != "auto":
                prompt_text = f"Transcribe the speech into text in {language}:"
            else:
                prompt_text = "Transcribe the speech into text:"

            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "audio", "audio_url": "placeholder"},
                    ],
                },
            ]

            # Apply chat template
            text = self._processor.apply_chat_template(
                conversation, add_generation_prompt=True, tokenize=False
            )

            # Process audio and text
            inputs = self._processor(
                text=text,
                audios=[audio_np],
                return_tensors="pt",
                padding=True,
            )

            # Move inputs to device
            inputs = {k: v.to(self._model.device) if hasattr(v, "to") else v
                     for k, v in inputs.items()}

            # Load generation parameters from settings
            try:
                from blaze.settings import Settings
                settings = Settings()
                temperature = float(settings.get("qwen_temperature", 0.7))
                top_p = float(settings.get("qwen_top_p", 0.9))
                top_k = int(settings.get("qwen_top_k", 50))
                max_new_tokens = int(settings.get("qwen_max_tokens", 256))
                repetition_penalty = float(settings.get("qwen_repetition_penalty", 1.1))
                do_sample = temperature > 0.1
            except Exception:
                # Fallback to defaults if settings fail
                temperature = 0.7
                top_p = 0.9
                top_k = 50
                max_new_tokens = 256
                repetition_penalty = 1.1
                do_sample = True

            logger.debug(
                f"Qwen generation params: temp={temperature}, top_p={top_p}, "
                f"top_k={top_k}, max_tokens={max_new_tokens}, "
                f"repetition_penalty={repetition_penalty}, do_sample={do_sample}"
            )

            # Generate
            generate_kwargs = {
                "max_new_tokens": max_new_tokens,
                "do_sample": do_sample,
            }

            if do_sample:
                generate_kwargs["temperature"] = temperature
                generate_kwargs["top_p"] = top_p
                generate_kwargs["top_k"] = top_k
                generate_kwargs["repetition_penalty"] = repetition_penalty

            with torch.no_grad():
                generate_ids = self._model.generate(**inputs, **generate_kwargs)

            # Remove input tokens from output
            generate_ids = generate_ids[:, inputs["input_ids"].size(1):]

            # Decode
            transcription = self._processor.batch_decode(
                generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            # Detect language from model output if possible, otherwise use hint
            detected_language = language

            return TranscriptionResult(
                text=transcription.strip(),
                language=detected_language,
                confidence=None,
            )

        except Exception as e:
            logger.error(f"Qwen transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if model is downloaded in HuggingFace cache"""
        if model_id in QWEN_MODELS:
            repo_id = QWEN_MODELS[model_id]
        elif model_id == "qwen2-audio-7b-instruct":
            repo_id = "Qwen/Qwen2-Audio-7B-Instruct"
        else:
            return False

        # Check HuggingFace cache with multiple methods
        try:
            from huggingface_hub import try_to_load_from_cache, scan_cache_dir

            # Method 1: Check individual files
            for filename in [
                "model.safetensors",
                "pytorch_model.bin",
                "model.fp16.safetensors",
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
        Download a Qwen model from HuggingFace.

        Args:
            model_id: Model to download
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        from huggingface_hub import snapshot_download

        if model_id not in QWEN_MODELS:
            logger.error(f"Unknown Qwen model: {model_id}")
            return False

        repo_id = QWEN_MODELS[model_id]

        try:
            logger.info(f"Downloading Qwen model: {repo_id}")
            if progress_callback:
                progress_callback(0)

            # Download with snapshot_download (uses default HF cache)
            snapshot_download(
                repo_id=repo_id,
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

        if model_id not in QWEN_MODELS:
            return False

        try:
            # Unload if currently loaded
            if self._loaded_model_id == model_id:
                self.unload()

            repo_id = QWEN_MODELS[model_id]

            # Find cache directory using HF's standard cache
            try:
                from huggingface_hub import try_to_load_from_cache, scan_cache_dir

                # First try: find config.json location
                config_path = try_to_load_from_cache(repo_id, "config.json")
                if config_path:
                    cache_dir = Path(config_path).parent
                    if cache_dir.exists():
                        logger.info(f"Deleting model cache: {cache_dir}")
                        shutil.rmtree(cache_dir)
                        return True

                # Second try: scan cache for this repo
                cache_info = scan_cache_dir()
                for repo in cache_info.repos:
                    if repo.repo_id == repo_id:
                        logger.info(f"Deleting repo from cache: {repo.repo_id}")
                        shutil.rmtree(repo.repo_path)
                        return True

            except Exception as e:
                logger.warning(f"Could not find cache dir for deletion: {e}")

            return False

        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return False
