"""
Qwen2-Audio Backend Implementation (GGUF via llama.cpp)

Speech-to-text using Alibaba's Qwen2-Audio models via llama-cpp-python.
Uses quantized GGUF models for efficient CPU inference with low memory usage.

Dependencies:
    pip install llama-cpp-python>=0.3.0
    pip install numpy
    pip install huggingface-hub

Models:
    - Qwen2-Audio-7B-Q4_K_M: 4-bit quantized (~4.2GB) - Good balance
    - Qwen2-Audio-7B-Q5_K_S: 5-bit quantized (~5.0GB) - Better quality
    - Qwen2-Audio-7B-Q6_K: 6-bit quantized (~6.4GB) - Very good quality
    - Qwen2-Audio-7B-Q8_0: 8-bit quantized (~8.3GB) - Best quality
    - All support Chinese, English, Japanese, Korean, Arabic, and more
    - Input: Raw audio bytes (16kHz PCM, mono)
    - License: Apache-2.0
"""

import os
import logging
from typing import Optional, Callable
from pathlib import Path

import numpy as np

from blaze.backends.base import (
    BaseModelBackend,
    TranscriptionResult,
    ModelNotFoundError,
    ModelLoadError,
    TranscriptionError,
)
from blaze.backends.registry import ModelRegistry

logger = logging.getLogger(__name__)

# Model definitions - GGUF quantized versions from mradermacher
QWEN_MODELS = {
    "qwen2-audio-7b-q4": {
        "repo_id": "mradermacher/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "Qwen2-Audio-7B.Q4_K_M.gguf",
        "mmproj_filename": "Qwen2-Audio-7B.mmproj-Q8_0.gguf",
    },
    "qwen2-audio-7b-q5": {
        "repo_id": "mradermacher/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "Qwen2-Audio-7B.Q5_K_S.gguf",
        "mmproj_filename": "Qwen2-Audio-7B.mmproj-Q8_0.gguf",
    },
    "qwen2-audio-7b-q6": {
        "repo_id": "mradermacher/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "Qwen2-Audio-7B.Q6_K.gguf",
        "mmproj_filename": "Qwen2-Audio-7B.mmproj-Q8_0.gguf",
    },
    "qwen2-audio-7b-q8": {
        "repo_id": "mradermacher/Qwen2-Audio-7B-GGUF",
        "gguf_filename": "Qwen2-Audio-7B.Q8_0.gguf",
        "mmproj_filename": "Qwen2-Audio-7B.mmproj-Q8_0.gguf",
    },
}


class QwenBackend(BaseModelBackend):
    """
    Qwen2-Audio backend for speech-to-text using llama.cpp.

    This backend uses llama-cpp-python to run quantized GGUF inference
    on Qwen's audio-language models with minimal memory usage.
    """

    def __init__(self):
        super().__init__()
        self._llm: Optional = None
        self._device: str = "cpu"
        self._loaded_model_id: Optional[str] = None
        self._gguf_path: Optional[Path] = None
        self._mmproj_path: Optional[Path] = None

    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a Qwen Audio model (GGUF quantized version via llama.cpp).

        Args:
            model_id: Model ID (e.g., 'qwen2-audio-7b-q4', 'qwen2-audio-7b-q6', 'qwen2-audio-7b-q8')
            device: 'cpu', 'cuda', or 'auto' (llama.cpp handles GPU automatically)
        """
        from llama_cpp import Llama

        # Validate model ID
        if model_id not in QWEN_MODELS:
            raise ModelNotFoundError(f"Unknown Qwen model: {model_id}")

        model_info = QWEN_MODELS[model_id]
        repo_id = model_info["repo_id"]
        gguf_filename = model_info["gguf_filename"]
        mmproj_filename = model_info["mmproj_filename"]

        # Determine device (llama.cpp handles GPU automatically via n_gpu_layers)
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device = device

        try:
            logger.info(f"Loading Qwen model: {model_id}")
            logger.info(f"GGUF file: {gguf_filename}")
            logger.info(f"MMProj file: {mmproj_filename}")
            logger.info(f"Device: {device}")

            # Get cached file paths
            from huggingface_hub import try_to_load_from_cache
            
            self._gguf_path = try_to_load_from_cache(repo_id, gguf_filename)
            self._mmproj_path = try_to_load_from_cache(repo_id, mmproj_filename)

            if self._gguf_path is None:
                raise ModelNotFoundError(
                    f"GGUF file not downloaded: {gguf_filename}. "
                    f"Please download the model first."
                )
            
            if self._mmproj_path is None:
                raise ModelNotFoundError(
                    f"MMProj file not downloaded: {mmproj_filename}. "
                    f"Please download the model first."
                )

            # Set GPU layers based on device
            n_gpu_layers = -1 if device == "cuda" else 0  # -1 = all layers on GPU

            # Load model with llama.cpp
            logger.info(f"Loading GGUF model with llama.cpp from {self._gguf_path}")
            
            self._llm = Llama(
                model_path=str(self._gguf_path),
                n_ctx=8192,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )

            # Load multimodal projector
            logger.info(f"Loading multimodal projector from {self._mmproj_path}")
            self._llm.load_multimodal_projector(str(self._mmproj_path))

            self._loaded_model_id = model_id
            logger.info(f"Successfully loaded {model_id} on {device}")

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def unload(self) -> None:
        """Unload the model to free memory"""
        if self._llm is not None:
            logger.info(f"Unloading Qwen model: {self._loaded_model_id}")
            del self._llm
            self._llm = None
            self._loaded_model_id = None
            self._gguf_path = None
            self._mmproj_path = None

            import gc
            gc.collect()

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio using Qwen2-Audio via llama.cpp.

        Args:
            audio_data: Raw audio bytes (16kHz PCM, mono)
            language: Optional language hint (e.g., 'en', 'zh')

        Returns:
            TranscriptionResult with text
        """
        if self._llm is None:
            raise TranscriptionError("Model not loaded. Call load() first.")

        try:
            import tempfile
            import wave
            import struct

            # Convert raw PCM bytes to proper WAV file
            # audio_data is 16-bit PCM, 16kHz, mono
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                
                # Convert bytes to int16 array
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Write as proper WAV file
                with wave.open(tmp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(16000)  # 16kHz
                    wav_file.writeframes(audio_array.tobytes())

            try:
                # Build prompt
                if language and language != "auto":
                    prompt = f"Transcribe the speech into text in {language}:"
                else:
                    prompt = "Transcribe the speech into text:"

                # Load generation parameters from settings
                try:
                    from blaze.settings import Settings
                    settings = Settings()
                    temperature = float(settings.get("qwen_temperature", 0.7))
                    top_p = float(settings.get("qwen_top_p", 0.9))
                    top_k = int(settings.get("qwen_top_k", 50))
                    max_tokens = int(settings.get("qwen_max_tokens", 256))
                except Exception:
                    temperature = 0.7
                    top_p = 0.9
                    top_k = 50
                    max_tokens = 256

                logger.debug(
                    f"Qwen generation params: temp={temperature}, top_p={top_p}, "
                    f"top_k={top_k}, max_tokens={max_tokens}"
                )

                # Generate with audio input via llama.cpp chat completion
                response = self._llm.create_chat_completion(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "audio", "audio_url": tmp_path},
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    max_tokens=max_tokens,
                )

                # Extract transcription
                transcription = response["choices"][0]["message"]["content"]

                return TranscriptionResult(
                    text=transcription.strip(),
                    language=language,
                    confidence=None,
                )

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Qwen transcription failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise TranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if GGUF model and mmproj files are downloaded"""
        if model_id not in QWEN_MODELS:
            # Support legacy model ID
            if model_id == "qwen2-audio-7b":
                model_id = "qwen2-audio-7b-q4"
            else:
                return False

        model_info = QWEN_MODELS[model_id]
        repo_id = model_info["repo_id"]
        gguf_filename = model_info["gguf_filename"]
        mmproj_filename = model_info["mmproj_filename"]

        try:
            from huggingface_hub import try_to_load_from_cache

            # Check both files exist
            gguf_path = try_to_load_from_cache(repo_id, gguf_filename)
            mmproj_path = try_to_load_from_cache(repo_id, mmproj_filename)

            if gguf_path is not None and mmproj_path is not None:
                logger.debug(f"Found {gguf_filename} and {mmproj_filename} for {model_id}")
                return True

            logger.debug(f"Missing files for {model_id}: gguf={gguf_path}, mmproj={mmproj_path}")
            return False

        except Exception as e:
            logger.debug(f"Error checking model cache: {e}")
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
        mmproj_filename = model_info["mmproj_filename"]

        try:
            logger.info(f"Downloading Qwen model: {model_id}")
            logger.info(f"GGUF file: {gguf_filename}")
            logger.info(f"MMProj file: {mmproj_filename}")
            if progress_callback:
                progress_callback(0)

            # Download main GGUF file
            logger.info(f"Downloading from {repo_id}")
            hf_hub_download(
                repo_id=repo_id,
                filename=gguf_filename,
                local_files_only=False,
            )
            if progress_callback:
                progress_callback(50)

            # Download multimodal projector
            logger.info(f"Downloading multimodal projector {mmproj_filename}")
            hf_hub_download(
                repo_id=repo_id,
                filename=mmproj_filename,
                local_files_only=False,
            )

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
            mmproj_filename = model_info["mmproj_filename"]

            # Find and delete GGUF file cache
            try:
                from huggingface_hub import try_to_load_from_cache

                # Delete main GGUF file
                gguf_path = try_to_load_from_cache(repo_id, gguf_filename)
                if gguf_path:
                    cache_dir = Path(gguf_path).parent
                    if cache_dir.exists():
                        logger.info(f"Deleting GGUF cache: {cache_dir}")
                        shutil.rmtree(cache_dir)

                # Delete mmproj file if exists (may be in same or different dir)
                mmproj_path = try_to_load_from_cache(repo_id, mmproj_filename)
                if mmproj_path:
                    mmproj_dir = Path(mmproj_path).parent
                    if mmproj_dir.exists() and mmproj_dir != cache_dir:
                        logger.info(f"Deleting mmproj cache: {mmproj_dir}")
                        shutil.rmtree(mmproj_dir)

                return True

            except Exception as e:
                logger.warning(f"Could not find cache dir for deletion: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return False
