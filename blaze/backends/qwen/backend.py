"""
Qwen2.5-Omni Backend Implementation (GGUF via llama.cpp CLI)

Speech-to-text using Alibaba's Qwen2.5-Omni multimodal models via llama-mtmd-cli.
Uses quantized GGUF models for efficient inference with low memory usage.

Dependencies:
    - llama.cpp compiled with llama-mtmd-cli binary
    - huggingface-hub (for model downloads)
    - numpy

Models:
    - Qwen2.5-Omni-7B-Q4: 4-bit quantized (~4.6GB) - Fast, recommended
    - Qwen2.5-Omni-7B-Q6: 6-bit quantized (~6.4GB) - Very good quality
    - Qwen2.5-Omni-7B-Q8: 8-bit quantized (~8.2GB) - Best quality
    - Qwen2.5-Omni-3B-Q4: 4-bit quantized (~3.5GB) - Smaller, faster
    - All support 10,000+ languages (Chinese, Arabic, Japanese, Korean, etc.)
    - Input: Audio files (WAV or MP3)
    - License: Apache-2.0

Note: Qwen2.5-Omni is significantly better than Qwen2-Audio (which has
hallucination issues in llama.cpp). This implementation uses llama-mtmd-cli
via subprocess instead of llama-cpp-python's Python API.
"""

import os
import subprocess
import logging
import shutil
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
    "qwen2.5-omni-7b-q4": {
        "repo_id": "mradermacher/Qwen2.5-Omni-7B-GGUF",
        "gguf_filename": "Qwen2.5-Omni-7B.Q4_K_M.gguf",
        "mmproj_filename": "Qwen2.5-Omni-7B.mmproj-Q8_0.gguf",
        "size_gb": 4.8,
    },
    "qwen2.5-omni-7b-q6": {
        "repo_id": "mradermacher/Qwen2.5-Omni-7B-GGUF",
        "gguf_filename": "Qwen2.5-Omni-7B.Q6_K.gguf",
        "mmproj_filename": "Qwen2.5-Omni-7B.mmproj-Q8_0.gguf",
        "size_gb": 6.4,
    },
    "qwen2.5-omni-7b-q8": {
        "repo_id": "mradermacher/Qwen2.5-Omni-7B-GGUF",
        "gguf_filename": "Qwen2.5-Omni-7B.Q8_0.gguf",
        "mmproj_filename": "Qwen2.5-Omni-7B.mmproj-Q8_0.gguf",
        "size_gb": 8.2,
    },
    "qwen2.5-omni-3b-q4": {
        "repo_id": "mradermacher/Qwen2.5-Omni-3B-GGUF",
        "gguf_filename": "Qwen2.5-Omni-3B.Q4_K_M.gguf",
        "mmproj_filename": "Qwen2.5-Omni-3B.mmproj-Q8_0.gguf",
        "size_gb": 2.5,
    },
}


class QwenBackend(BaseModelBackend):
    """
    Qwen2.5-Omni backend for speech-to-text using llama.cpp CLI.

    This backend uses llama-mtmd-cli (multimodal CLI) to run quantized GGUF
    inference on Qwen's multimodal models via subprocess.
    """

    def __init__(self):
        super().__init__()
        self._device: str = "cpu"
        self._loaded_model_id: Optional[str] = None
        self._gguf_path: Optional[Path] = None
        self._mmproj_path: Optional[Path] = None
        self._llama_cli_path: Optional[Path] = None

    def load(self, model_id: str, device: str = "auto") -> None:
        """
        Load a Qwen2.5-Omni model (GGUF quantized version via llama.cpp CLI).

        Args:
            model_id: Model ID (e.g., 'qwen2.5-omni-7b-q4', 'qwen2.5-omni-7b-q6')
            device: 'cpu', 'cuda', or 'auto'
        """
        # Validate model ID
        if model_id not in QWEN_MODELS:
            raise ModelNotFoundError(f"Unknown Qwen model: {model_id}")

        model_info = QWEN_MODELS[model_id]
        repo_id = model_info["repo_id"]
        gguf_filename = model_info["gguf_filename"]
        mmproj_filename = model_info["mmproj_filename"]

        # Determine device
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._device = device

        try:
            logger.info(f"Loading Qwen2.5-Omni model: {model_id}")
            logger.info(f"GGUF file: {gguf_filename}")
            logger.info(f"MMProj file: {mmproj_filename}")
            logger.info(f"Device: {device}")

            # Find llama-mtmd-cli binary
            self._llama_cli_path = self._find_llama_cli()
            if not self._llama_cli_path:
                raise ModelLoadError(
                    "llama-mtmd-cli not found. Please install llama.cpp and ensure "
                    "llama-mtmd-cli is in your PATH or in ~/.local/bin/"
                )

            logger.info(f"Using llama-mtmd-cli: {self._llama_cli_path}")

            # Get cached file paths from HuggingFace
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

            # Verify files exist
            if not Path(self._gguf_path).exists():
                raise ModelLoadError(f"GGUF file not found: {self._gguf_path}")
            if not Path(self._mmproj_path).exists():
                raise ModelLoadError(f"MMProj file not found: {self._mmproj_path}")

            self._loaded_model_id = model_id
            logger.info(f"Successfully loaded {model_id} (files verified)")

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")

    def _find_llama_cli(self) -> Optional[Path]:
        """Find llama-mtmd-cli binary in common locations"""
        # Check PATH first
        cli_path = shutil.which("llama-mtmd-cli")
        if cli_path:
            return Path(cli_path)

        # Check common locations
        common_paths = [
            Path.home() / ".local" / "bin" / "llama-mtmd-cli",
            Path("/usr/local/bin/llama-mtmd-cli"),
            Path("/usr/bin/llama-mtmd-cli"),
            Path.home() / "llama.cpp" / "bin" / "llama-mtmd-cli",
        ]

        for path in common_paths:
            if path.exists() and path.is_file():
                return path

        return None

    def unload(self) -> None:
        """Unload the model (no-op for CLI-based backend)"""
        if self._loaded_model_id is not None:
            logger.info(f"Unloading Qwen model: {self._loaded_model_id}")
            self._loaded_model_id = None
            self._gguf_path = None
            self._mmproj_path = None

            import gc
            gc.collect()

    def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio using Qwen2.5-Omni via llama-mtmd-cli.

        Args:
            audio_data: Raw audio bytes (16kHz PCM, mono)
            language: Optional language hint (e.g., 'en', 'zh')

        Returns:
            TranscriptionResult with text
        """
        if self._loaded_model_id is None:
            raise TranscriptionError("Model not loaded. Call load() first.")

        try:
            import tempfile
            import wave

            # Convert raw PCM bytes to WAV file (llama-mtmd-cli needs WAV/MP3)
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
                    temperature = float(settings.get("qwen_temperature", 0.1))
                    top_p = float(settings.get("qwen_top_p", 0.8))
                    top_k = int(settings.get("qwen_top_k", 100))
                    max_tokens = int(settings.get("qwen_max_tokens", 512))
                except Exception:
                    temperature = 0.1
                    top_p = 0.8
                    top_k = 100
                    max_tokens = 512

                logger.debug(
                    f"Qwen generation params: temp={temperature}, top_p={top_p}, "
                    f"top_k={top_k}, max_tokens={max_tokens}"
                )

                # Build llama-mtmd-cli command
                n_gpu_layers = 999 if self._device == "cuda" else 0

                cmd = [
                    str(self._llama_cli_path),
                    "-m", str(self._gguf_path),
                    "--mmproj", str(self._mmproj_path),
                    "--audio", tmp_path,
                    "--prompt", prompt,
                    "--ctx-size", "8192",
                    "-ngl", str(n_gpu_layers),
                    "--temp", str(temperature),
                    "--top-p", str(top_p),
                    "--top-k", str(top_k),
                    "-n", str(max_tokens),
                    "--repeat-penalty", "1.05",
                    "--log-disable",  # Disable llama.cpp logging
                ]

                logger.debug(f"Running llama-mtmd-cli: {' '.join(cmd)}")

                # Run llama-mtmd-cli and capture output
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                )

                if result.returncode != 0:
                    raise TranscriptionError(
                        f"llama-mtmd-cli failed with code {result.returncode}: "
                        f"{result.stderr}"
                    )

                # Extract transcription from stdout
                transcription = result.stdout.strip()

                # Remove common llama.cpp output artifacts
                # The actual transcription usually starts after the prompt
                if prompt in transcription:
                    transcription = transcription.split(prompt, 1)[1].strip()

                # Remove any llama.cpp metadata (lines starting with special chars)
                lines = transcription.split('\n')
                clean_lines = [
                    line for line in lines
                    if line and not line.startswith(('llama', 'ggml', 'system_info'))
                ]
                transcription = '\n'.join(clean_lines).strip()

                if not transcription:
                    logger.warning("Empty transcription from llama-mtmd-cli")
                    transcription = ""

                return TranscriptionResult(
                    text=transcription,
                    language=language,
                    confidence=None,
                )

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except subprocess.TimeoutExpired:
            logger.error("llama-mtmd-cli timed out after 120 seconds")
            raise TranscriptionError("Transcription timed out")
        except Exception as e:
            logger.error(f"Qwen transcription failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise TranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if GGUF model and mmproj files are downloaded"""
        if model_id not in QWEN_MODELS:
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
        Download a Qwen2.5-Omni GGUF model from HuggingFace.

        Args:
            model_id: Model to download (e.g., 'qwen2.5-omni-7b-q4')
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
            logger.info(f"Downloading Qwen2.5-Omni model: {model_id}")
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
