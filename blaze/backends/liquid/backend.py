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
                self._processor = self._processor.cuda()

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
            chat.add_text("Transcribe the speech into text.")
            chat.end_turn()

            # User turn with audio
            chat.new_turn("user")
            chat.add_audio(wav, sample_rate)
            chat.end_turn()

            chat.new_turn("assistant")

            # Generate text tokens only (sequential generation for ASR)
            text_tokens = []
            for t in self._model.generate_sequential(
                **chat, max_new_tokens=512, temperature=0.7, top_k=50
            ):
                if t.numel() == 1:
                    text_tokens.append(t)

            # Decode text
            if text_tokens:
                text_tensor = torch.stack(text_tokens, 1)
                transcription = self._processor.text.decode(text_tensor[0])
            else:
                transcription = ""

            return TranscriptionResult(
                text=transcription.strip(),
                language="en",  # Model only supports English
                confidence=None,
            )

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if model is downloaded in HuggingFace cache"""
        if model_id not in LIQUID_MODELS:
            return False

        repo_id = LIQUID_MODELS[model_id]

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
