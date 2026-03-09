"""
Unified Model Registry

Central registry for all STT models across all backends.
Provides model metadata, capabilities, and hardware requirements.
"""

from typing import Dict, List, Optional
from .base import ModelCapability, ModelTier


# Unified registry of all available models
# Maps model_id -> ModelCapability
UNIFIED_MODEL_REGISTRY: Dict[str, ModelCapability] = {
    # =========================================================================
    # WHISPER MODELS
    # =========================================================================
    # Ultra-light tier (< 2GB RAM)
    "whisper-tiny": ModelCapability(
        model_id="whisper-tiny",
        backend="whisper",
        name="Whisper Tiny",
        description="Fastest model, basic accuracy (39MB). Good for CPU-only systems.",
        size_mb=39,
        min_ram_gb=0.5,
        recommended_ram_gb=1.0,
        min_vram_gb=None,
        languages=["all"],
        tier=ModelTier.ULTRA_LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-tiny",
        language_performance={"all": 0.75},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-tiny.en": ModelCapability(
        model_id="whisper-tiny.en",
        backend="whisper",
        name="Whisper Tiny (English)",
        description="English-only, fastest for English speech (39MB)",
        size_mb=39,
        min_ram_gb=0.5,
        recommended_ram_gb=1.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.ULTRA_LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-tiny.en",
        language_performance={"en": 0.76},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-base": ModelCapability(
        model_id="whisper-base",
        backend="whisper",
        name="Whisper Base",
        description="Good balance of speed and accuracy (74MB)",
        size_mb=74,
        min_ram_gb=1.0,
        recommended_ram_gb=2.0,
        min_vram_gb=None,
        languages=["all"],
        tier=ModelTier.ULTRA_LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-base",
        language_performance={"all": 0.78},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-base.en": ModelCapability(
        model_id="whisper-base.en",
        backend="whisper",
        name="Whisper Base (English)",
        description="English-only, better accuracy for English (74MB)",
        size_mb=74,
        min_ram_gb=1.0,
        recommended_ram_gb=2.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.ULTRA_LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-base.en",
        language_performance={"en": 0.79},
        gpu_preference="gpu_agnostic",
    ),
    # Light tier (2-4GB RAM)
    "whisper-small": ModelCapability(
        model_id="whisper-small",
        backend="whisper",
        name="Whisper Small",
        description="Better accuracy, still fast (244MB)",
        size_mb=244,
        min_ram_gb=2.0,
        recommended_ram_gb=4.0,
        min_vram_gb=None,
        languages=["all"],
        tier=ModelTier.LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-small",
        language_performance={"all": 0.82},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-small.en": ModelCapability(
        model_id="whisper-small.en",
        backend="whisper",
        name="Whisper Small (English)",
        description="English-only, good accuracy (244MB)",
        size_mb=244,
        min_ram_gb=2.0,
        recommended_ram_gb=4.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-small.en",
        language_performance={"en": 0.84},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-distil-small.en": ModelCapability(
        model_id="whisper-distil-small.en",
        backend="whisper",
        name="Distil-Whisper Small (English)",
        description="Distilled for speed, English-only (400MB)",
        size_mb=400,
        min_ram_gb=2.0,
        recommended_ram_gb=4.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.LIGHT,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-distil-whisper-small.en",
        language_performance={"en": 0.83},
        gpu_preference="gpu_agnostic",
    ),
    # Medium tier (4-8GB RAM)
    "whisper-medium": ModelCapability(
        model_id="whisper-medium",
        backend="whisper",
        name="Whisper Medium",
        description="High accuracy, multilingual (769MB)",
        size_mb=769,
        min_ram_gb=4.0,
        recommended_ram_gb=8.0,
        min_vram_gb=None,
        languages=["all"],
        tier=ModelTier.MEDIUM,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-medium",
        language_performance={"all": 0.89},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-medium.en": ModelCapability(
        model_id="whisper-medium.en",
        backend="whisper",
        name="Whisper Medium (English)",
        description="High accuracy, English-only (769MB)",
        size_mb=769,
        min_ram_gb=4.0,
        recommended_ram_gb=8.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.MEDIUM,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-medium.en",
        language_performance={"en": 0.90},
        gpu_preference="gpu_agnostic",
    ),
    "whisper-distil-medium.en": ModelCapability(
        model_id="whisper-distil-medium.en",
        backend="whisper",
        name="Distil-Whisper Medium (English)",
        description="Distilled for speed, high accuracy (1.2GB)",
        size_mb=1200,
        min_ram_gb=4.0,
        recommended_ram_gb=8.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.MEDIUM,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-distil-whisper-medium.en",
        language_performance={"en": 0.89},
        gpu_preference="gpu_agnostic",
    ),
    # Heavy tier (8GB+ RAM)
    "whisper-large-v2": ModelCapability(
        model_id="whisper-large-v2",
        backend="whisper",
        name="Whisper Large v2",
        description="Excellent accuracy, large model (2.4GB)",
        size_mb=2400,
        min_ram_gb=6.0,
        recommended_ram_gb=10.0,
        min_vram_gb=4.0,
        languages=["all"],
        tier=ModelTier.HEAVY,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-large-v2",
        language_performance={"all": 0.93},
        gpu_preference="gpu_preferred",
    ),
    "whisper-large-v3": ModelCapability(
        model_id="whisper-large-v3",
        backend="whisper",
        name="Whisper Large v3",
        description="Best Whisper accuracy (3.1GB)",
        size_mb=3100,
        min_ram_gb=6.0,
        recommended_ram_gb=12.0,
        min_vram_gb=4.0,
        languages=["all"],
        tier=ModelTier.HEAVY,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-large-v3",
        language_performance={"all": 0.95},
        gpu_preference="gpu_preferred",
    ),
    "whisper-large-v3-turbo": ModelCapability(
        model_id="whisper-large-v3-turbo",
        backend="whisper",
        name="Whisper Large v3 Turbo",
        description="Large v3 accuracy with faster inference (3.1GB)",
        size_mb=3100,
        min_ram_gb=6.0,
        recommended_ram_gb=12.0,
        min_vram_gb=4.0,
        languages=["all"],
        tier=ModelTier.HEAVY,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-whisper-large-v3-turbo",
        language_performance={"all": 0.94},
        gpu_preference="gpu_preferred",
    ),
    "whisper-distil-large-v2": ModelCapability(
        model_id="whisper-distil-large-v2",
        backend="whisper",
        name="Distil-Whisper Large v2",
        description="Distilled large model, good speed/accuracy (2.4GB)",
        size_mb=2400,
        min_ram_gb=6.0,
        recommended_ram_gb=10.0,
        min_vram_gb=4.0,
        languages=["all"],
        tier=ModelTier.HEAVY,
        license="MIT",
        supports_word_timestamps=True,
        repo_id="Systran/faster-distil-whisper-large-v2",
        language_performance={"all": 0.94},
        gpu_preference="gpu_preferred",
    ),
    # =========================================================================
    # IBM GRANITE SPEECH MODELS - DISABLED (requires GraniteSpeechModel which
    # is not available in current transformers version)
    # =========================================================================
    # "granite-speech-3.3-2b": ModelCapability(
    #     model_id="granite-speech-3.3-2b",
    #     backend="granite",
    #     name="Granite Speech 3.3-2B",
    #     description="IBM's enterprise ASR. Excellent for EN, FR, DE, ES, PT. Supports translation to JA, ZH (4GB)",
    #     size_mb=4000,
    #     min_ram_gb=4.0,
    #     recommended_ram_gb=6.0,
    #     min_vram_gb=None,  # CPU-friendly
    #     languages=["en", "fr", "de", "es", "pt"],
    #     tier=ModelTier.LIGHT,
    #     license="Apache-2.0",
    #     supports_word_timestamps=False,
    #     repo_id="ibm-granite/granite-speech-3.3-2b",
    #     language_performance={
    #         "en": 0.95,
    #         "fr": 0.95,
    #         "de": 0.95,
    #         "es": 0.90,
    #         "pt": 0.90,
    #         "it": 0.75,
    #         "nl": 0.75,
    #         "pl": 0.70,
    #         "ja": 0.65,
    #         "zh": 0.65,
    #         "ru": 0.70,
    #     },
    #     gpu_preference="gpu_agnostic",
    # ),
    # =========================================================================
    # LIQUID AI MODELS
    # =========================================================================
    "lfm2.5-audio-1.5b": ModelCapability(
        model_id="lfm2.5-audio-1.5b",
        backend="liquid",
        name="LFM2.5-Audio 1.5B",
        description="Liquid AI end-to-end audio model. Optimized for on-device, conversational ASR (3GB)",
        size_mb=3000,
        min_ram_gb=3.0,
        recommended_ram_gb=4.0,
        min_vram_gb=None,
        languages=["en"],
        tier=ModelTier.LIGHT,
        license="LFM-Open-1.0",
        is_streaming=True,
        supports_word_timestamps=False,
        repo_id="LiquidAI/LFM2.5-Audio-1.5B",
        language_performance={"en": 0.95},
        gpu_preference="gpu_agnostic",
    ),
    # =========================================================================
    # QWEN MODELS (GGUF Quantized versions from mradermacher)
    # =========================================================================
    "qwen2-audio-7b-q4": ModelCapability(
        model_id="qwen2-audio-7b-q4",
        backend="qwen",
        name="Qwen2-Audio 7B (Q4_K_M)",
        description="Alibaba's multilingual audio model - 4-bit quantized (4.2GB). Good balance of quality and memory usage.",
        size_mb=4200,
        min_ram_gb=6.0,
        recommended_ram_gb=8.0,
        min_vram_gb=None,  # Works on CPU
        languages=["zh", "en", "ja", "ko", "ar", "fr", "de", "es", "it", "pt", "ru", "all"],
        tier=ModelTier.MEDIUM,
        license="Apache-2.0",
        supports_word_timestamps=False,
        repo_id="mradermacher/Qwen2-Audio-7B-GGUF",
        gguf_filename="Qwen2-Audio-7B.Q4_K_M.gguf",
        language_performance={
            "zh": 0.90,
            "en": 0.88,
            "ja": 0.83,
            "ko": 0.81,
            "ar": 0.78,
        },
        gpu_preference="cpu_preferred",  # GGUF runs well on CPU
        is_streaming=False,
    ),
    "qwen2-audio-7b-q5": ModelCapability(
        model_id="qwen2-audio-7b-q5",
        backend="qwen",
        name="Qwen2-Audio 7B (Q5_K_S)",
        description="Alibaba's multilingual audio model - 5-bit quantized (~5GB). Better quality than Q4.",
        size_mb=5000,
        min_ram_gb=7.0,
        recommended_ram_gb=9.0,
        min_vram_gb=None,  # Works on CPU
        languages=["zh", "en", "ja", "ko", "ar", "fr", "de", "es", "it", "pt", "ru", "all"],
        tier=ModelTier.MEDIUM,
        license="Apache-2.0",
        supports_word_timestamps=False,
        repo_id="mradermacher/Qwen2-Audio-7B-GGUF",
        gguf_filename="Qwen2-Audio-7B.Q5_K_S.gguf",
        language_performance={
            "zh": 0.91,
            "en": 0.89,
            "ja": 0.84,
            "ko": 0.82,
            "ar": 0.79,
        },
        gpu_preference="cpu_preferred",  # GGUF runs well on CPU
        is_streaming=False,
    ),
    "qwen2-audio-7b-q6": ModelCapability(
        model_id="qwen2-audio-7b-q6",
        backend="qwen",
        name="Qwen2-Audio 7B (Q6_K)",
        description="Alibaba's multilingual audio model - 6-bit quantized (6.4GB). Very good quality with moderate memory.",
        size_mb=6400,
        min_ram_gb=8.0,
        recommended_ram_gb=10.0,
        min_vram_gb=None,  # Works on CPU
        languages=["zh", "en", "ja", "ko", "ar", "fr", "de", "es", "it", "pt", "ru", "all"],
        tier=ModelTier.MEDIUM,
        license="Apache-2.0",
        supports_word_timestamps=False,
        repo_id="mradermacher/Qwen2-Audio-7B-GGUF",
        gguf_filename="Qwen2-Audio-7B.Q6_K.gguf",
        language_performance={
            "zh": 0.91,
            "en": 0.89,
            "ja": 0.84,
            "ko": 0.82,
            "ar": 0.79,
        },
        gpu_preference="cpu_preferred",  # GGUF runs well on CPU
        is_streaming=False,
    ),
    "qwen2-audio-7b-q8": ModelCapability(
        model_id="qwen2-audio-7b-q8",
        backend="qwen",
        name="Qwen2-Audio 7B (Q8_0)",
        description="Alibaba's multilingual audio model - 8-bit quantized (8.3GB). Best quality quantized version.",
        size_mb=8300,
        min_ram_gb=10.0,
        recommended_ram_gb=12.0,
        min_vram_gb=None,  # Works on CPU
        languages=["zh", "en", "ja", "ko", "ar", "fr", "de", "es", "it", "pt", "ru", "all"],
        tier=ModelTier.HEAVY,
        license="Apache-2.0",
        supports_word_timestamps=False,
        repo_id="mradermacher/Qwen2-Audio-7B-GGUF",
        gguf_filename="Qwen2-Audio-7B.Q8_0.gguf",
        language_performance={
            "zh": 0.92,
            "en": 0.90,
            "ja": 0.85,
            "ko": 0.83,
            "ar": 0.80,
        },
        gpu_preference="cpu_preferred",  # GGUF runs well on CPU
        is_streaming=False,
    ),
}


class ModelRegistry:
    """
    Central registry for all STT models.

    Provides query methods to find models by backend, language,
    hardware compatibility, etc.
    """

    @classmethod
    def get_all_models(cls) -> List[ModelCapability]:
        """Get all registered models"""
        return list(UNIFIED_MODEL_REGISTRY.values())

    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelCapability]:
        """Get a specific model by ID"""
        return UNIFIED_MODEL_REGISTRY.get(model_id)

    @classmethod
    def get_models_for_backend(cls, backend: str) -> List[ModelCapability]:
        """Get all models for a specific backend"""
        return [m for m in UNIFIED_MODEL_REGISTRY.values() if m.backend == backend]

    @classmethod
    def get_models_for_language(cls, language: str) -> List[ModelCapability]:
        """
        Get all models that support a specific language.

        Args:
            language: Language code (e.g., 'en', 'fr') or 'all' for multilingual
        """
        results = []
        for model in UNIFIED_MODEL_REGISTRY.values():
            if language == "all":
                # Multilingual mode: include models that support "all" OR have 3+ languages
                if "all" in model.languages or len(model.languages) >= 3:
                    results.append(model)
            elif "all" in model.languages or language in model.languages:
                results.append(model)
        return results

    @classmethod
    def get_models_by_tier(cls, tier: ModelTier) -> List[ModelCapability]:
        """Get all models in a specific hardware tier"""
        return [m for m in UNIFIED_MODEL_REGISTRY.values() if m.tier == tier]

    @classmethod
    def get_available_backends(cls) -> List[str]:
        """Get list of all backend names"""
        backends = set(m.backend for m in UNIFIED_MODEL_REGISTRY.values())
        return sorted(list(backends))

    @classmethod
    def get_backend_for_model(cls, model_id: str) -> Optional[str]:
        """Get the backend type for a specific model ID.

        Args:
            model_id: The model ID to look up

        Returns:
            Backend name (e.g., 'whisper', 'liquid', 'granite') or None if model not found
        """
        model = cls.get_model(model_id)
        return model.backend if model else None

    @classmethod
    def get_compatibility_info(
        cls,
        model_id: str,
        total_ram_gb: float,
        available_ram_gb: float,
        gpu_available: bool = False,
        gpu_memory_gb: Optional[List[float]] = None,
    ) -> Dict:
        """
        Check if a model is compatible with the current system.

        Returns a dict with:
            - compatible: bool
            - reason: str (explanation if not compatible)
            - recommended: bool (whether it's recommended for this system)
        """
        model = cls.get_model(model_id)
        if not model:
            return {
                "compatible": False,
                "reason": f"Unknown model: {model_id}",
                "recommended": False,
            }

        # Check RAM
        if available_ram_gb < model.min_ram_gb:
            return {
                "compatible": False,
                "reason": f"Needs {model.min_ram_gb}GB RAM available, have {available_ram_gb:.1f}GB",
                "recommended": False,
            }

        # Check VRAM if specified
        if model.min_vram_gb is not None:
            if not gpu_available:
                return {
                    "compatible": False,
                    "reason": f"Needs GPU with {model.min_vram_gb}GB VRAM, no GPU detected",
                    "recommended": False,
                }

            total_vram = sum(gpu_memory_gb) if gpu_memory_gb else 0
            if total_vram < model.min_vram_gb:
                return {
                    "compatible": False,
                    "reason": f"Needs {model.min_vram_gb}GB VRAM, have {total_vram:.1f}GB",
                    "recommended": False,
                }

        # Check if recommended (has recommended RAM amount)
        recommended = available_ram_gb >= model.recommended_ram_gb

        return {
            "compatible": True,
            "reason": "Compatible with your system",
            "recommended": recommended,
        }

    @classmethod
    def get_compatible_models(
        cls,
        available_ram_gb: float,
        gpu_available: bool = False,
        gpu_memory_gb: Optional[List[float]] = None,
        language: Optional[str] = None,
    ) -> List[ModelCapability]:
        """
        Get all models compatible with the given hardware and optionally language.
        """
        compatible = []
        for model in UNIFIED_MODEL_REGISTRY.values():
            info = cls.get_compatibility_info(
                model.model_id,
                available_ram_gb
                + model.min_ram_gb,  # Assume total is at least min more than available
                available_ram_gb,
                gpu_available,
                gpu_memory_gb,
            )
            if info["compatible"]:
                if (
                    language is None
                    or "all" in model.languages
                    or language in model.languages
                ):
                    compatible.append(model)
        return compatible

    @classmethod
    def get_recommended_models(
        cls,
        available_ram_gb: float,
        gpu_available: bool = False,
        gpu_memory_gb: Optional[List[float]] = None,
        language: Optional[str] = None,
    ) -> List[ModelCapability]:
        """
        Get models that are not just compatible, but recommended for the system.
        """
        all_compatible = cls.get_compatible_models(
            available_ram_gb, gpu_available, gpu_memory_gb, language
        )
        return [m for m in all_compatible if available_ram_gb >= m.recommended_ram_gb]
