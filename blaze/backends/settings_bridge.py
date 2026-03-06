"""
Enhanced SettingsBridge with Multi-Backend Model Support

This module provides additional methods to the SettingsBridge for the new
multi-backend STT system. It adds hardware detection and model compatibility
features while maintaining backward compatibility with existing code.
"""

import logging
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import pyqtSlot, pyqtProperty, pyqtSignal, QObject

from blaze.backends.registry import ModelRegistry, ModelCapability
from blaze.backends.coordinator import get_coordinator
from blaze.system.resource_detector import detect_resources

logger = logging.getLogger(__name__)


class ModelSettingsBridge(QObject):
    """
    Extended settings bridge for multi-backend model management.

    This class provides QML-accessible methods for:
    - Hardware resource detection
    - Model compatibility checking
    - Unified model registry access
    - Backend management
    """

    # Signals
    hardwareInfoChanged = pyqtSignal()
    compatibleModelsChanged = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._coordinator = get_coordinator()
        self._cached_resources = None

    # === Hardware Information ===

    @pyqtSlot(result="QVariantMap")
    def getHardwareInfo(self) -> Dict[str, Any]:
        """
        Get system hardware information.

        Returns dict with:
        - total_ram_gb: Total system RAM
        - available_ram_gb: Available RAM
        - cpu_count: Number of CPU cores
        - gpu_available: Whether GPU is detected
        - gpu_count: Number of GPUs
        - gpu_memory_gb: List of GPU memory sizes
        - gpu_names: List of GPU names
        - is_laptop: Whether system is a laptop
        - recommended_tier: Recommended model tier (ultra_light/light/medium/heavy)
        """
        try:
            resources = detect_resources()
            info = resources.to_dict()
            logger.info(f"Hardware info: {info}")
            return info
        except Exception as e:
            logger.error(f"Failed to detect hardware: {e}")
            return {
                "total_ram_gb": 8.0,
                "available_ram_gb": 4.0,
                "cpu_count": 4,
                "gpu_available": False,
                "gpu_count": 0,
                "gpu_memory_gb": None,
                "gpu_names": None,
                "is_laptop": False,
                "recommended_tier": "light",
                "error": str(e),
            }

    # === Model Registry Access ===

    @pyqtSlot(result="QVariantList")
    def getAllModels(self) -> List[Dict[str, Any]]:
        """
        Get all available models from the unified registry.

        Returns list of model dicts with compatibility information.
        """
        try:
            resources = detect_resources()
            models = ModelRegistry.get_all_models()
            current_model = self._settings.get("model", "whisper-tiny")

            result = []
            for model in models:
                compat = ModelRegistry.get_compatibility_info(
                    model.model_id,
                    resources.total_ram_gb,
                    resources.available_ram_gb,
                    resources.gpu_available,
                    resources.gpu_memory_gb,
                )

                result.append(
                    {
                        "id": model.model_id,
                        "name": model.name,
                        "backend": model.backend,
                        "description": model.description,
                        "size_mb": model.size_mb,
                        "size": self._format_size(model.size_mb),
                        "languages": model.languages,
                        "tier": model.tier.value,
                        "license": model.license,
                        "compatible": compat["compatible"],
                        "compatibility_reason": compat["reason"],
                        "recommended": compat["recommended"],
                        "downloaded": self._coordinator.is_model_downloaded(
                            model.model_id
                        ),
                        "active": model.model_id == current_model,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    @pyqtSlot(str, result="QVariantList")
    def getModelsForBackend(self, backend: str) -> List[Dict[str, Any]]:
        """Get all models for a specific backend"""
        try:
            resources = detect_resources()
            models = ModelRegistry.get_models_for_backend(backend)
            current_model = self._settings.get("model", "whisper-tiny")

            result = []
            for model in models:
                compat = ModelRegistry.get_compatibility_info(
                    model.model_id,
                    resources.total_ram_gb,
                    resources.available_ram_gb,
                    resources.gpu_available,
                    resources.gpu_memory_gb,
                )

                result.append(
                    {
                        "id": model.model_id,
                        "name": model.name,
                        "description": model.description,
                        "size": self._format_size(model.size_mb),
                        "languages": model.languages,
                        "compatible": compat["compatible"],
                        "compatibility_reason": compat["reason"],
                        "recommended": compat["recommended"],
                        "downloaded": self._coordinator.is_model_downloaded(
                            model.model_id
                        ),
                        "active": model.model_id == current_model,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to get models for backend {backend}: {e}")
            return []

    @pyqtSlot(str, result="QVariantList")
    def getModelsForLanguage(self, language: str) -> List[Dict[str, Any]]:
        """Get all models that support a specific language"""
        try:
            resources = detect_resources()
            models = ModelRegistry.get_models_for_language(language)
            current_model = self._settings.get("model", "whisper-tiny")

            result = []
            for model in models:
                compat = ModelRegistry.get_compatibility_info(
                    model.model_id,
                    resources.total_ram_gb,
                    resources.available_ram_gb,
                    resources.gpu_available,
                    resources.gpu_memory_gb,
                )

                result.append(
                    {
                        "id": model.model_id,
                        "name": model.name,
                        "backend": model.backend,
                        "description": model.description,
                        "size": self._format_size(model.size_mb),
                        "compatible": compat["compatible"],
                        "downloaded": self._coordinator.is_model_downloaded(
                            model.model_id
                        ),
                        "active": model.model_id == current_model,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to get models for language {language}: {e}")
            return []

    @pyqtSlot(result="QVariantList")
    def getCompatibleModels(self) -> List[Dict[str, Any]]:
        """Get only models compatible with current hardware"""
        try:
            resources = detect_resources()
            language = self._settings.get("language", "auto")
            if language == "auto":
                language = None

            models = ModelRegistry.get_compatible_models(
                available_ram_gb=resources.available_ram_gb,
                gpu_available=resources.gpu_available,
                gpu_memory_gb=resources.gpu_memory_gb,
                language=language,
            )

            current_model = self._settings.get("model", "whisper-tiny")

            result = []
            for model in models:
                result.append(
                    {
                        "id": model.model_id,
                        "name": model.name,
                        "backend": model.backend,
                        "description": model.description,
                        "size": self._format_size(model.size_mb),
                        "languages": model.languages,
                        "tier": model.tier.value,
                        "downloaded": self._coordinator.is_model_downloaded(
                            model.model_id
                        ),
                        "active": model.model_id == current_model,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to get compatible models: {e}")
            return []

    @pyqtSlot(result="QVariantMap")
    def getRecommendedModel(self) -> Optional[Dict[str, Any]]:
        """Get the best model recommendation for current hardware"""
        try:
            from blaze.system.resource_detector import ResourceDetector

            detector = ResourceDetector()
            resources = detector.detect()
            language = self._settings.get("language", None)
            if language == "auto":
                language = None

            model = detector.get_best_model_for_system(ModelRegistry, language)

            if model:
                return {
                    "id": model.model_id,
                    "name": model.name,
                    "backend": model.backend,
                    "description": model.description,
                    "size": self._format_size(model.size_mb),
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get recommended model: {e}")
            return None

    # === Backend Management ===

    @pyqtSlot(result="QVariantList")
    def getAvailableBackends(self) -> List[str]:
        """Get list of available backend names"""
        return self._coordinator.get_available_backends()

    @pyqtSlot(str, result=bool)
    def isBackendAvailable(self, backend: str) -> bool:
        """Check if a backend is available"""
        return self._coordinator.is_backend_available(backend)

    # === Model Operations ===

    @pyqtSlot(str)
    def downloadModel(self, model_id: str):
        """Download a model with progress tracking"""
        import threading

        def progress_callback(progress: int):
            # This would need to be connected to parent's signal
            logger.info(f"Download progress for {model_id}: {progress}%")

        def download_thread():
            try:
                success = self._coordinator.download_model(model_id, progress_callback)
                if success:
                    logger.info(f"Download complete: {model_id}")
                else:
                    logger.error(f"Download failed: {model_id}")
            except Exception as e:
                logger.error(f"Download error for {model_id}: {e}")

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    @pyqtSlot(str)
    def deleteModel(self, model_id: str):
        """Delete a downloaded model"""
        try:
            self._coordinator.delete_model(model_id)
            logger.info(f"Deleted model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")

    @pyqtSlot(str)
    def setActiveModel(self, model_id: str):
        """Set the active model"""
        logger.info(f"Setting active model: {model_id}")
        self._settings.set("model", model_id)

    @pyqtSlot(str, result=bool)
    def isModelDownloaded(self, model_id: str) -> bool:
        """Check if a model is downloaded"""
        return self._coordinator.is_model_downloaded(model_id)

    # === Utility Methods ===

    def _format_size(self, size_mb: int) -> str:
        """Format size in MB to human-readable string"""
        if size_mb >= 1000:
            return f"{size_mb / 1024:.1f} GB"
        return f"{size_mb} MB"
