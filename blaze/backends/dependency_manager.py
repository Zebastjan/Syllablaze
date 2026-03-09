"""
Dependency Manager for Optional Backends

Handles installation of backend dependencies when users want to use
optional backends like Liquid, Granite, or Qwen.
"""

import subprocess
import sys
import logging
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


# Dependencies required by each backend
BACKEND_DEPENDENCIES = {
    "liquid": {
        "packages": ["liquid-audio", "torchaudio"],
        "optional": ["flash-attn"],
        "description": "Liquid AI LFM2.5-Audio",
        "size_estimate": "~3GB download",
        "install_command": "pip install liquid-audio torchaudio",
    },
    "granite": {
        "packages": ["transformers>=4.40.0", "torchaudio", "peft", "soundfile"],
        "optional": [],
        "description": "IBM Granite Speech",
        "size_estimate": "~4GB download",
        "install_command": "pip install transformers>=4.40.0 torchaudio peft soundfile",
    },
    "qwen": {
        "packages": ["llama-cpp-python>=0.3.0"],
        "optional": [],
        "description": "Qwen2-Audio ASR with llama.cpp GGUF inference",
        "size_estimate": "~4-8GB download (quantized)",
        "install_command": "pip install 'llama-cpp-python>=0.3.0'",
    },
}


class DependencyManager:
    """Manages installation of optional backend dependencies"""

    @classmethod
    def get_backend_info(cls, backend: str) -> Optional[dict]:
        """Get information about a backend's dependencies"""
        return BACKEND_DEPENDENCIES.get(backend)

    @classmethod
    def is_backend_available(cls, backend: str) -> bool:
        """Check if a backend's dependencies are installed"""
        try:
            if backend == "liquid":
                import liquid_audio
                import torchaudio
                return True
            elif backend == "granite":
                import transformers
                import torchaudio
                import peft
                import soundfile
                return True
            elif backend == "qwen":
                import llama_cpp
                return True
        except ImportError:
            pass
        return False

    @classmethod
    def install_backend(
        cls,
        backend: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        include_optional: bool = False,
    ) -> bool:
        """
        Install dependencies for a backend.

        Args:
            backend: Backend name (liquid, granite, qwen)
            progress_callback: Optional callback(message, progress_percent)
            include_optional: Whether to install optional dependencies

        Returns:
            True if installation succeeded
        """
        info = BACKEND_DEPENDENCIES.get(backend)
        if not info:
            logger.error(f"Unknown backend: {backend}")
            return False

        packages = info["packages"].copy()
        if include_optional and info["optional"]:
            packages.extend(info["optional"])

        logger.info(f"Installing dependencies for {backend}: {packages}")

        if progress_callback:
            progress_callback(f"Installing {info['description']}...", 0)

        try:
            # Build pip install command
            cmd = [sys.executable, "-m", "pip", "install"] + packages

            logger.info(f"Running: {' '.join(cmd)}")

            # Run pip install
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Stream output
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"pip: {line}")
                    if progress_callback:
                        # Simple progress based on keywords
                        if "Collecting" in line:
                            progress_callback(f"Downloading packages...", 25)
                        elif "Installing" in line or "Building" in line:
                            progress_callback(f"Installing packages...", 50)
                        elif "Successfully" in line:
                            progress_callback(f"Installation complete!", 100)

            process.wait()

            if process.returncode == 0:
                logger.info(f"Successfully installed {backend} dependencies")
                if progress_callback:
                    progress_callback(
                        f"{info['description']} installed successfully!", 100
                    )
                return True
            else:
                logger.error(
                    f"Installation failed with return code {process.returncode}"
                )
                return False

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            if progress_callback:
                progress_callback(f"Installation failed: {e}", 0)
            return False

    @classmethod
    def get_install_command(cls, backend: str) -> str:
        """Get the pip install command for a backend"""
        info = BACKEND_DEPENDENCIES.get(backend)
        if not info:
            return ""

        packages = " ".join(info["packages"])
        return f"pip install {packages}"


def install_liquid_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """Convenience function to install Liquid backend"""
    return DependencyManager.install_backend("liquid", progress_callback)


def install_granite_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """Convenience function to install Granite backend"""
    return DependencyManager.install_backend("granite", progress_callback)


def install_qwen_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """Convenience function to install Qwen backend"""
    return DependencyManager.install_backend("qwen", progress_callback)
