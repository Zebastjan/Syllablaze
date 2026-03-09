"""
Qwen2-Audio Backend Implementation (GGUF Quantized)

Speech-to-text using Alibaba's Qwen2-Audio models via transformers with GGUF quantization.
Uses NexaAI's quantized GGUF models for dramatically lower memory usage.

Dependencies:
    pip install git+https://github.com/huggingface/transformers
    pip install torchaudio librosa
    pip install huggingface-hub

Models:
    - Qwen2-Audio-7B-Q4_K_M: 4-bit quantized (~4.2GB) - Good balance
    - Qwen2-Audio-7B-Q6_K: 6-bit quantized (~6.5GB) - Very good quality
    - Qwen2-Audio-7B-Q8_0: 8-bit quantized (~8.3GB) - Best quality
    - All support Chinese, English, Japanese, Korean, Arabic, and more
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

# Model definitions - GGUF quantized versions from NexaAI
QWEN_MODELS = {
    "qwen2-audio-7b-q4": {
        "repo_id": "NexaAI/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "qwen2-audio-7b-q4_K_M.gguf",
        "base_repo": "Qwen/Qwen2-Audio-7B",  # For tokenizer/processor
    },
    "qwen2-audio-7b-q6": {
        "repo_id": "NexaAI/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "qwen2-audio-7b-Q6_K.gguf",
        "base_repo": "Qwen/Qwen2-Audio-7B",
    },
    "qwen2-audio-7b-q8": {
        "repo_id": "NexaAI/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "qwen2-audio-7b-Q8_0.gguf",
        "base_repo": "Qwen/Qwen2-Audio-7B",
    },
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
        Load a Qwen Audio model (GGUF quantized version).

        Args:
            model_id: Model ID (e.g., 'qwen2-audio-7b-q4', 'qwen2-audio-7b-q6', 'qwen2-audio-7b-q8')
            device: 'cpu', 'cuda', or 'auto'
        """
        from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

        # Validate model ID
        if model_id not in QWEN_MODELS:
            raise ModelNotFoundError(f"Unknown Qwen model: {model_id}")

        model_info = QWEN_MODELS[model_id]
        repo_id = model_info["repo_id"]
        gguf_filename = model_info["gguf_filename"]
        base_repo = model_info["base_repo"]

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device = device

        try:
            logger.info(f"Loading Qwen model: {model_id}")
            logger.info(f"GGUF file: {gguf_filename}")
            logger.info(f"Device: {device}")

            # Load processor from base repo (tokenizer is same for all quantizations)
            logger.info(f"Loading processor from {base_repo}")
            self._processor = AutoProcessor.from_pretrained(base_repo)

            # Load model with GGUF file
            logger.info(f"Loading GGUF model from {repo_id}/{gguf_filename}")
            
            # For GGUF models, transformers handles device automatically
            # but we can specify torch_dtype based on device
            if device == "cuda":
                torch_dtype = torch.float16
            else:
                torch_dtype = torch.float32

            self._model = Qwen2AudioForConditionalGeneration.from_pretrained(
                repo_id,
                gguf_file=gguf_filename,
                torch_dtype=torch_dtype,
            )
            
            # Move to device if needed (GGUF loading may handle this)
            if hasattr(self._model, 'device') and str(self._model.device) != device:
                self._model = self._model.to(device)

            self._model.eval()

            self._loaded_model_id = model_id
            logger.info(f"Successfully loaded {model_id} on {device}")

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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

            # Build transcription prompt with audio tokens
            # Use the language hint in the prompt if provided
            if language and language != "auto":
                prompt_text = f"<|audio_bos|><|AUDIO|><|audio_eos|>Transcribe the speech into text in {language}:"
            else:
                prompt_text = "<|audio_bos|><|AUDIO|><|audio_eos|>Transcribe the speech into text:"

            # Process audio and text
            inputs = self._processor(
                text=prompt_text,
                audio=audio_np,
                sampling_rate=16000,
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
        """Check if GGUF model file is downloaded in HuggingFace cache"""
        if model_id not in QWEN_MODELS:
            # Support legacy model ID
            if model_id == "qwen2-audio-7b":
                model_id = "qwen2-audio-7b-q4"  # Default to Q4
            else:
                return False

        model_info = QWEN_MODELS[model_id]
        repo_id = model_info["repo_id"]
        gguf_filename = model_info["gguf_filename"]

        # Check if GGUF file exists in cache
        try:
            from huggingface_hub import try_to_load_from_cache

            model_path = try_to_load_from_cache(repo_id, gguf_filename)
            if model_path is not None:
                logger.debug(f"Found {gguf_filename} for {model_id}")
                return True

        except Exception as e:
            logger.debug(f"Error checking model cache: {e}")

        logger.debug(f"Model {model_id} not found in cache")
        return False

    def download_model(
        self, model_id: str, progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """
        Download a Qwen GGUF model from HuggingFace.

        Args:
            model_id: Model to download (e.g., 'qwen2-audio-7b-q4')
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        from huggingface_hub import hf_hub_download

        if model_id not in QWEN_MODELS:
            logger.error(f"Unknown Qwen model: {model_id}")
            return False

        model_info = QWEN_MODELS[model_id]
        repo_id = model_info["repo_id"]
        gguf_filename = model_info["gguf_filename"]
        base_repo = model_info["base_repo"]

        try:
            logger.info(f"Downloading Qwen model: {model_id}")
            logger.info(f"GGUF file: {gguf_filename}")
            if progress_callback:
                progress_callback(0)

            # Download the GGUF file specifically
            logger.info(f"Downloading from {repo_id}")
            hf_hub_download(
                repo_id=repo_id,
                filename=gguf_filename,
                local_files_only=False,
            )

            # Also download tokenizer files from base repo (needed for processor)
            logger.info(f"Downloading tokenizer from {base_repo}")
            for tokenizer_file in ["config.json", "tokenizer.json", "tokenizer_config.json", "preprocessor_config.json"]:
                try:
                    hf_hub_download(
                        repo_id=base_repo,
                        filename=tokenizer_file,
                        local_files_only=False,
                    )
                    logger.info(f"Downloaded {tokenizer_file}")
                except Exception as e:
                    logger.warning(f"Could not download {tokenizer_file}: {e}")

            logger.info(f"Successfully downloaded {model_id}")
            if progress_callback:
                progress_callback(100)
            return True

        except Exception as e:
            logger.error(f"Failed to download {model_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
            # Support legacy model ID
            if model_id == "qwen2-audio-7b":
                model_id = "qwen2-audio-7b-q4"
            else:
                return False

        try:
            # Unload if currently loaded
            if self._loaded_model_id == model_id:
                self.unload()

            model_info = QWEN_MODELS[model_id]
            repo_id = model_info["repo_id"]
            gguf_filename = model_info["gguf_filename"]
            base_repo = model_info["base_repo"]

            # Find and delete GGUF file cache
            try:
                from huggingface_hub import try_to_load_from_cache, scan_cache_dir

                # Delete GGUF file
                gguf_path = try_to_load_from_cache(repo_id, gguf_filename)
                if gguf_path:
                    cache_dir = Path(gguf_path).parent
                    if cache_dir.exists():
                        logger.info(f"Deleting GGUF cache: {cache_dir}")
                        shutil.rmtree(cache_dir)

                # Delete base repo files (tokenizer, config)
                for file in ["config.json", "tokenizer.json", "preprocessor_config.json"]:
                    file_path = try_to_load_from_cache(base_repo, file)
                    if file_path:
                        # Delete parent directory for this repo
                        base_cache_dir = Path(file_path).parent.parent  # Go up to repo level
                        if base_cache_dir.exists() and "Qwen" in str(base_cache_dir):
                            logger.info(f"Deleting base repo cache: {base_cache_dir}")
                            shutil.rmtree(base_cache_dir)
                            break  # Only delete once

                return True

            except Exception as e:
                logger.warning(f"Could not find cache dir for deletion: {e}")

            return False

        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return False
