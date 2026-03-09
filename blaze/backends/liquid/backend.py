"""
Liquid AI LFM2.5-Audio Backend

Speech-to-text using Liquid AI's LFM2.5-Audio-1.5B model.

Dependencies:
    pip install liquid-audio torchaudio

Optional:
    pip install flash-attn --no-build-isolation

Model info:
    - 1.5B parameters (1.2B LM + 115M audio encoder)
    - Supports English only
    - Input: 24kHz audio (model will resample if needed)
    - License: LFM Open License v1.0
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
LIQUID_MODELS = {
    "lfm2.5-audio-1.5b": "LiquidAI/LFM2.5-Audio-1.5B",
}


class LiquidBackend(BaseModelBackend):
    """
    Liquid AI LFM2.5-Audio backend for speech-to-text.

    This backend uses the liquid-audio package to run inference
    on Liquid AI's end-to-end audio foundation model.
    """

    def __init__(self):
        super().__init__()
        self._processor: Optional = None
        self._model: Optional = None
        self._device: str = "cpu"
        self._cache_dir = Path.home() / ".cache" / "syllablaze" / "liquid"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a Liquid Audio model.

        Args:
            model_id: Model ID (e.g., 'lfm2.5-audio-1.5b')
            device: 'cpu', 'cuda', or 'auto'
        """
        from liquid_audio import LFM2AudioModel, LFM2AudioProcessor

        # Validate model ID
        if model_id not in LIQUID_MODELS:
            raise ModelNotFoundError(f"Unknown Liquid model: {model_id}")

        repo_id = LIQUID_MODELS[model_id]

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device = device

        try:
            logger.info(f"Loading Liquid model: {model_id} from {repo_id}")
            logger.info(f"Device: {device}")

            # Load processor and model
            self._processor = LFM2AudioProcessor.from_pretrained(repo_id)
            self._model = LFM2AudioModel.from_pretrained(repo_id)

            # Move to device
            if device == "cuda" and torch.cuda.is_available():
                self._model = self._model.cuda()
                # NOTE: processor is NOT moved to CUDA - only the model is
                # LFM2AudioProcessor is a utility class, not a PyTorch module

            self._model.eval()

            self._loaded_model_id = model_id
            logger.info(f"Successfully loaded {model_id}")

        except Exception as e:
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def unload(self) -> None:
        """Unload the model to free memory"""
        if self._model is not None:
            logger.info(f"Unloading Liquid model: {self._loaded_model_id}")
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
        Transcribe audio using LFM2.5-Audio.

        Args:
            audio_data: Raw audio bytes (16kHz or 24kHz PCM, mono)
            language: Optional (ignored, model only supports English)

        Returns:
            TranscriptionResult with text
        """
        if self._model is None or self._processor is None:
            raise TranscriptionError("Model not loaded. Call load() first.")

        try:
            from liquid_audio import ChatState

            # Convert bytes to numpy array (assuming 16kHz PCM input)
            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Convert to torch tensor and add batch dimension
            wav = torch.from_numpy(audio_np).unsqueeze(0)  # [1, samples]

            # Resample from 16kHz to 24kHz if needed
            # LFM2.5-Audio expects 24kHz
            sample_rate = 16000  # Assuming input is 16kHz
            if sample_rate != 24000:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, new_freq=24000
                )
                wav = resampler(wav)
                sample_rate = 24000

            # Move to device
            if self._device == "cuda" and torch.cuda.is_available():
                wav = wav.cuda()

            # Set up chat state for ASR
            chat = ChatState(self._processor)

            # System prompt for transcription
            chat.new_turn("system")
            chat.add_text(
                "Transcribe the speech into text verbatim. Do not add commentary or repetition."
            )
            chat.end_turn()

            # User turn with audio
            chat.new_turn("user")
            chat.add_audio(wav, sample_rate)
            chat.end_turn()

            chat.new_turn("assistant")

            # Load generation parameters from settings
            try:
                from blaze.settings import Settings
                settings = Settings()
                max_new_tokens = int(settings.get("liquid_max_tokens", 200))
                text_temperature = float(settings.get("liquid_temperature", 0.3))
                text_top_k = int(settings.get("liquid_top_k", 50))
            except Exception:
                # Fallback to defaults if settings fail
                max_new_tokens = 200
                text_temperature = 0.3
                text_top_k = 50

            logger.debug(
                f"Liquid generation params: temp={text_temperature}, top_k={text_top_k}, max_tokens={max_new_tokens}"
            )

            # Generate text tokens only (sequential generation for ASR)
            text_tokens = []
            for t in self._model.generate_sequential(
                **chat,
                max_new_tokens=max_new_tokens,
                text_temperature=text_temperature,
                text_top_k=text_top_k,
            ):
                if t.numel() == 1:
                    text_tokens.append(t)

            # Decode text - filter out special tokens first
            if text_tokens:
                # Get special token IDs to filter out
                special_ids = set(self._processor.text.all_special_ids)
                # Also filter out common chat/control tokens
                try:
                    im_end_id = self._processor.text.convert_tokens_to_ids("<|im_end|>")
                    im_start_id = self._processor.text.convert_tokens_to_ids(
                        "<|im_start|>"
                    )
                    special_ids.update([im_end_id, im_start_id])
                except:
                    pass

                filtered_tokens = [
                    t for t in text_tokens if t.item() not in special_ids
                ]

                if filtered_tokens:
                    text_tensor = torch.stack(filtered_tokens, 1)
                    transcription = self._processor.text.decode(text_tensor[0])
                else:
                    transcription = ""
            else:
                transcription = ""

            # Post-processing: remove repetition patterns
            transcription = self._remove_repetition(transcription)

            return TranscriptionResult(
                text=transcription.strip(),
                language="en",  # Model only supports English
                confidence=None,
            )

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def _remove_repetition(self, text: str, max_repeats: int = 3) -> str:
        """
        Remove repetitive patterns from transcription.

        Args:
            text: Input text that may contain repetition
            max_repeats: Maximum allowed consecutive repeats of a phrase

        Returns:
            Text with repetition removed
        """
        import re

        # Split into sentences/phrases
        sentences = re.split(r"([.!?]+|\n)", text)

        result = []
        repeat_count = 0
        last_phrase = ""

        for i, sentence in enumerate(sentences):
            # Normalize for comparison (lowercase, strip whitespace)
            normalized = sentence.lower().strip()

            if not normalized:
                # Keep punctuation as-is
                if sentence.strip() in ".!?":
                    if result and not result[-1].endswith(sentence.strip()):
                        result.append(sentence)
                continue

            # Check if this is a repetition
            if normalized == last_phrase:
                repeat_count += 1
                if repeat_count >= max_repeats:
                    # Stop adding repetitions
                    break
            else:
                repeat_count = 0
                last_phrase = normalized

            result.append(sentence)

        return "".join(result).strip()

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if model is downloaded in HuggingFace cache"""
        # Map from registry model_id to internal key if needed
        if model_id in LIQUID_MODELS:
            repo_id = LIQUID_MODELS[model_id]
        elif model_id == "lfm2.5-audio-1.5b":
            repo_id = "LiquidAI/LFM2.5-Audio-1.5B"
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
        Download a Liquid model from HuggingFace.

        Args:
            model_id: Model to download
            progress_callback: Optional callback(progress_percent: int)

        Returns:
            True if download succeeded
        """
        from huggingface_hub import snapshot_download

        if model_id not in LIQUID_MODELS:
            logger.error(f"Unknown Liquid model: {model_id}")
            return False

        repo_id = LIQUID_MODELS[model_id]

        try:
            logger.info(f"Downloading Liquid model: {repo_id}")
            if progress_callback:
                progress_callback(0)

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

        if model_id not in LIQUID_MODELS:
            return False

        try:
            # Unload if currently loaded
            if self._loaded_model_id == model_id:
                self.unload()

            repo_id = LIQUID_MODELS[model_id]

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
