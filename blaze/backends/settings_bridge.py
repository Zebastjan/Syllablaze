"""
Enhanced SettingsBridge with Multi-Backend Model Support

This module provides additional methods to the SettingsBridge for the new
multi-backend STT system. It adds hardware detection and model compatibility
features while maintaining backward compatibility with existing code.
"""

import logging
import threading
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import pyqtSlot, pyqtProperty, pyqtSignal, QObject

from blaze.backends.registry import ModelRegistry, ModelCapability
from blaze.backends.coordinator import get_coordinator
from blaze.backends.dependency_manager import DependencyManager
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
    - Dependency management for optional backends
    """

    # Signals
    hardwareInfoChanged = pyqtSignal()
    compatibleModelsChanged = pyqtSignal()
    modelDownloadProgress = pyqtSignal(str, int)
    modelDownloadComplete = pyqtSignal(str)
    modelDownloadError = pyqtSignal(str, str)
    dependencyInstallProgress = pyqtSignal(str, str, int)
    dependencyInstallComplete = pyqtSignal(str, bool)
    backendAvailabilityChanged = pyqtSignal(str, bool)

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

    @pyqtSlot(str, result="QVariant")
    def isBackendAvailable(self, backend: str) -> bool:
        """Check if a backend is available"""
        return self._coordinator.is_backend_available(backend)

    # === Dependency Management ===

    @pyqtSlot(str, result="QVariantMap")
    def getBackendDependencyInfo(self, backend: str) -> Dict[str, Any]:
        """
        Get dependency information for a backend.

        Returns dict with:
        - available: Whether backend is currently available
        - packages: List of required packages
        - install_command: Command to install dependencies
        - description: Human-readable description
        - size_estimate: Estimated download size
        """
        info = DependencyManager.get_backend_info(backend)
        if not info:
            return {
                "available": False,
                "error": f"Unknown backend: {backend}",
            }

        return {
            "available": DependencyManager.is_backend_available(backend),
            "packages": info["packages"],
            "install_command": info["install_command"],
            "description": info["description"],
            "size_estimate": info["size_estimate"],
        }

    @pyqtSlot(str, result="QVariant")
    def checkBackendDependencies(self, backend: str) -> bool:
        """Check if a backend's dependencies are installed"""
        return DependencyManager.is_backend_available(backend)

    @pyqtSlot(str)
    def installBackendDependencies(self, backend: str):
        """
        Install dependencies for a backend.
        Emits dependencyInstallProgress and dependencyInstallComplete signals.
        """

        def progress_callback(message: str, progress: int):
            self.dependencyInstallProgress.emit(backend, message, progress)

        def install_thread():
            try:
                logger.info(f"Starting dependency installation for {backend}")
                self.dependencyInstallProgress.emit(
                    backend, "Starting installation...", 0
                )

                success = DependencyManager.install_backend(backend, progress_callback)

                if success:
                    logger.info(f"Successfully installed {backend} dependencies")
                    self.dependencyInstallComplete.emit(backend, True)
                    self.backendAvailabilityChanged.emit(backend, True)
                else:
                    logger.error(f"Failed to install {backend} dependencies")
                    self.dependencyInstallComplete.emit(backend, False)

            except Exception as e:
                logger.error(f"Installation error for {backend}: {e}")
                self.dependencyInstallProgress.emit(backend, f"Error: {str(e)}", 0)
                self.dependencyInstallComplete.emit(backend, False)

        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

    @pyqtSlot(str, result="QVariantList")
    def getAllBackendsWithStatus(self) -> List[Dict[str, Any]]:
        """
        Get all backends with their availability status.

        Returns list of dicts with:
        - name: Backend name
        - available: Whether available
        - description: Human-readable description
        - size_estimate: Download size estimate
        - install_command: Installation command
        """
        from blaze.backends.registry import ModelRegistry

        result = []
        all_backends = ["whisper", "granite", "liquid", "qwen"]

        for backend in all_backends:
            info = DependencyManager.get_backend_info(backend)
            if info:
                result.append(
                    {
                        "name": backend,
                        "available": DependencyManager.is_backend_available(backend),
                        "description": info["description"],
                        "packages": info["packages"],
                        "size_estimate": info["size_estimate"],
                        "install_command": info["install_command"],
                        "models_available": len(
                            ModelRegistry.get_models_for_backend(backend)
                        ),
                    }
                )
            elif backend == "whisper":
                # Whisper is always available (core dependency)
                result.append(
                    {
                        "name": "whisper",
                        "available": True,
                        "description": "OpenAI Whisper via faster-whisper",
                        "packages": ["faster-whisper"],
                        "size_estimate": "~80MB",
                        "install_command": "pip install faster-whisper",
                        "models_available": len(
                            ModelRegistry.get_models_for_backend("whisper")
                        ),
                    }
                )

        return result

    @pyqtSlot(str, result="QVariant")
    def getBackendForModel(self, model_id: str) -> Optional[str]:
        """Get the backend name for a specific model"""
        model = ModelRegistry.get_model(model_id)
        if model:
            return model.backend
        return None

    @pyqtSlot(str, result="QVariant")
    def canDownloadModel(self, model_id: str):
        """Check if a model can be downloaded (backend available)"""
        model = ModelRegistry.get_model(model_id)
        if not model:
            return False
        return self._coordinator.is_backend_available(model.backend)

    @pyqtSlot(str, result="QVariant")
    def isModelDownloaded(self, model_id: str):
        """Check if a model is downloaded"""
        return bool(self._coordinator.is_model_downloaded(model_id))

    # === Utility Methods ===

    def _format_size(self, size_mb: int) -> str:
        """Format size in MB to human-readable string"""
        if size_mb >= 1000:
            return f"{size_mb / 1024:.1f} GB"
        return f"{size_mb} MB"

    # === Backend-Specific Settings ===

    @pyqtSlot(result="QVariantMap")
    def getLiquidSettings(self) -> Dict[str, Any]:
        """
        Get Liquid backend generation settings.

        Returns dict with:
        - temperature: Generation temperature (0.0-1.0)
        - top_k: Top-k sampling value
        - max_tokens: Maximum tokens to generate
        """
        return {
            "temperature": self._settings.get("liquid_temperature", 0.3),
            "top_k": self._settings.get("liquid_top_k", 50),
            "max_tokens": self._settings.get("liquid_max_tokens", 1024),
        }

    @pyqtSlot(float)
    def setLiquidTemperature(self, value: float):
        """Set Liquid generation temperature (0.0-1.0)"""
        if 0.0 <= value <= 1.0:
            self._settings.set("liquid_temperature", value)
            logger.info(f"Liquid temperature set to {value}")
        else:
            logger.warning(f"Invalid liquid temperature: {value}")

    @pyqtSlot(int)
    def setLiquidTopK(self, value: int):
        """Set Liquid top-k sampling value"""
        if 1 <= value <= 100:
            self._settings.set("liquid_top_k", value)
            logger.info(f"Liquid top_k set to {value}")
        else:
            logger.warning(f"Invalid liquid top_k: {value}")

    @pyqtSlot(int)
    def setLiquidMaxTokens(self, value: int):
        """Set Liquid max tokens to generate"""
        if 100 <= value <= 2048:
            self._settings.set("liquid_max_tokens", value)
            logger.info(f"Liquid max_tokens set to {value}")
        else:
            logger.warning(f"Invalid liquid max_tokens: {value}")

    @pyqtSlot(result="QVariantMap")
    def getQwenSettings(self) -> Dict[str, Any]:
        """
        Get Qwen backend generation settings.

        Returns dict with:
        - temperature: Generation temperature (0.0-1.0)
        - top_p: Nucleus sampling threshold (0.0-1.0)
        - top_k: Top-k sampling value
        - max_tokens: Maximum tokens to generate
        - repetition_penalty: Penalty for repeated tokens (1.0-2.0)
        """
        return {
            "temperature": self._settings.get("qwen_temperature", 0.7),
            "top_p": self._settings.get("qwen_top_p", 0.9),
            "top_k": self._settings.get("qwen_top_k", 50),
            "max_tokens": self._settings.get("qwen_max_tokens", 256),
            "repetition_penalty": self._settings.get("qwen_repetition_penalty", 1.1),
        }

    @pyqtSlot(float)
    def setQwenTemperature(self, value: float):
        """Set Qwen generation temperature (0.0-1.0)"""
        if 0.0 <= value <= 1.0:
            self._settings.set("qwen_temperature", value)
            logger.info(f"Qwen temperature set to {value}")
        else:
            logger.warning(f"Invalid qwen temperature: {value}")

    @pyqtSlot(float)
    def setQwenTopP(self, value: float):
        """Set Qwen nucleus sampling threshold (0.0-1.0)"""
        if 0.0 <= value <= 1.0:
            self._settings.set("qwen_top_p", value)
            logger.info(f"Qwen top_p set to {value}")
        else:
            logger.warning(f"Invalid qwen top_p: {value}")

    @pyqtSlot(int)
    def setQwenTopK(self, value: int):
        """Set Qwen top-k sampling value"""
        if 1 <= value <= 100:
            self._settings.set("qwen_top_k", value)
            logger.info(f"Qwen top_k set to {value}")
        else:
            logger.warning(f"Invalid qwen top_k: {value}")

    @pyqtSlot(int)
    def setQwenMaxTokens(self, value: int):
        """Set Qwen max tokens to generate"""
        if 50 <= value <= 500:
            self._settings.set("qwen_max_tokens", value)
            logger.info(f"Qwen max_tokens set to {value}")
        else:
            logger.warning(f"Invalid qwen max_tokens: {value}")

    @pyqtSlot(float)
    def setQwenRepetitionPenalty(self, value: float):
        """Set Qwen repetition penalty (1.0-2.0)"""
        if 1.0 <= value <= 2.0:
            self._settings.set("qwen_repetition_penalty", value)
            logger.info(f"Qwen repetition_penalty set to {value}")
        else:
            logger.warning(f"Invalid qwen repetition_penalty: {value}")

    @pyqtSlot(result=str)
    def getQwenDevice(self) -> str:
        """Get Qwen device preference (cpu or cuda)"""
        return self._settings.get("qwen_device", "cuda")  # Default to CUDA if available

    @pyqtSlot(str)
    def setQwenDevice(self, value: str):
        """Set Qwen device preference (cpu or cuda)"""
        if value in ["cpu", "cuda"]:
            self._settings.set("qwen_device", value)
            logger.info(f"Qwen device set to {value}")
        else:
            logger.warning(f"Invalid qwen device: {value}")
