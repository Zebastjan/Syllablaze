"""
Whisper model management package for Syllablaze

This package provides components for managing Whisper models:
- Model registry with metadata
- Model path utilities
- Model download functionality
- High-level model manager API
"""

from blaze.models.registry import FASTER_WHISPER_MODELS, ModelRegistry
from blaze.models.paths import ModelPaths
from blaze.models.manager import WhisperModelManager

__all__ = [
    "FASTER_WHISPER_MODELS",
    "ModelRegistry",
    "ModelPaths",
    "WhisperModelManager",
]
