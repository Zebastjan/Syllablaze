"""
STT Backends Package

Provides a unified interface for multiple speech-to-text backends:
- whisper: OpenAI Whisper via faster-whisper (default)
- granite: IBM Granite Speech models
- liquid: Liquid AI LFM2.5-Audio models
- qwen: Qwen ASR models (future)
"""

from blaze.backends.base import (
    BaseModelBackend,
    BaseTranscriber,
    TranscriptionResult,
    ModelCapability,
    ModelTier,
    BackendError,
    ModelNotFoundError,
    ModelLoadError,
    TranscriptionError,
)
from blaze.backends.registry import ModelRegistry, UNIFIED_MODEL_REGISTRY
from blaze.backends.coordinator import BackendCoordinator, get_coordinator
from blaze.backends.dependency_manager import DependencyManager

__all__ = [
    # Base classes
    "BaseModelBackend",
    "BaseTranscriber",
    "TranscriptionResult",
    "ModelCapability",
    "ModelTier",
    "BackendError",
    "ModelNotFoundError",
    "ModelLoadError",
    "TranscriptionError",
    # Registry
    "ModelRegistry",
    "UNIFIED_MODEL_REGISTRY",
    # Coordinator
    "BackendCoordinator",
    "get_coordinator",
    # Dependency management
    "DependencyManager",
]
