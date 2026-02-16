"""
Whisper Model Registry

Provides metadata and information about available Whisper models.
"""

import logging

logger = logging.getLogger(__name__)


# Define Faster Whisper model information
FASTER_WHISPER_MODELS = {
    # Standard Whisper models
    "tiny": {"size_mb": 75, "description": "Tiny model (75MB)", "type": "standard"},
    "tiny.en": {
        "size_mb": 75,
        "description": "Tiny English-only model (75MB)",
        "type": "standard",
    },
    "base": {"size_mb": 142, "description": "Base model (142MB)", "type": "standard"},
    "base.en": {
        "size_mb": 142,
        "description": "Base English-only model (142MB)",
        "type": "standard",
    },
    "small": {"size_mb": 466, "description": "Small model (466MB)", "type": "standard"},
    "small.en": {
        "size_mb": 466,
        "description": "Small English-only model (466MB)",
        "type": "standard",
    },
    "medium": {
        "size_mb": 1500,
        "description": "Medium model (1.5GB)",
        "type": "standard",
    },
    "medium.en": {
        "size_mb": 1500,
        "description": "Medium English-only model (1.5GB)",
        "type": "standard",
    },
    "large-v1": {
        "size_mb": 2900,
        "description": "Large v1 model (2.9GB)",
        "type": "standard",
    },
    "large-v2": {
        "size_mb": 3000,
        "description": "Large v2 model (3.0GB)",
        "type": "standard",
    },
    "large-v3": {
        "size_mb": 3100,
        "description": "Large v3 model (3.1GB)",
        "type": "standard",
    },
    "large-v3-turbo": {
        "size_mb": 3100,
        "description": "Large v3 Turbo model - Faster with similar accuracy (3.1GB)",
        "type": "standard",
    },
    "large": {
        "size_mb": 3100,
        "description": "Large model (3.1GB)",
        "type": "standard",
    },
    # Distil-Whisper models (CTranslate2-converted by Systran for faster-whisper)
    # NOTE: Using Systran's faster-distil-whisper versions which are pre-converted to CTranslate2 format
    # The original distil-whisper models are in safetensors format and won't work with faster-whisper
    "distil-medium.en": {
        "size_mb": 1200,
        "description": "Distilled Medium English-only model (1.2GB)",
        "type": "distil",
        "repo_id": "Systran/faster-distil-whisper-medium.en",
    },
    "distil-large-v2": {
        "size_mb": 2400,
        "description": "Distilled Large v2 model (2.4GB)",
        "type": "distil",
        "repo_id": "Systran/faster-distil-whisper-large-v2",
    },
    "distil-small.en": {
        "size_mb": 400,
        "description": "Distilled Small English-only model (400MB)",
        "type": "distil",
        "repo_id": "Systran/faster-distil-whisper-small.en",
    },
}


class ModelRegistry:
    """Registry for Whisper model information"""

    # Use the existing FASTER_WHISPER_MODELS dictionary
    MODELS = FASTER_WHISPER_MODELS

    @classmethod
    def get_model_info(cls, model_name):
        """Get information for a specific model"""
        return cls.MODELS.get(model_name, {})

    @classmethod
    def get_all_models(cls):
        """Get list of all available models"""
        return list(cls.MODELS.keys())

    @classmethod
    def is_distil_model(cls, model_name):
        """Check if a model is a distil-whisper model"""
        return cls.get_model_info(model_name).get("type") == "distil"

    @classmethod
    def get_repo_id(cls, model_name):
        """Get the repository ID for a model"""
        return cls.get_model_info(model_name).get("repo_id")

    @classmethod
    def add_model(cls, model_name, model_info):
        """Add a new model to the registry"""
        cls.MODELS[model_name] = model_info
        logger.info(f"Added new model to registry: {model_name}")

    @classmethod
    def update_from_huggingface(cls):
        """Update the registry with models from Hugging Face"""
        try:
            # This would be implemented to query Hugging Face API
            # For now, we'll just use the existing models
            pass
        except Exception as e:
            logger.warning(f"Failed to update model registry from Hugging Face: {e}")
