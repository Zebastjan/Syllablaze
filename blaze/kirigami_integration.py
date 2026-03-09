"""
Kirigami Integration Layer for Syllablaze

This module replaces PyQt6 SettingsWindow with Kirigami QML interface.
"""

import os
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QUrl, Qt
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QDesktopServices

from blaze.settings import Settings
from blaze.constants import (
    APP_NAME,
    APP_VERSION,
    GITHUB_REPO_URL,
    SAMPLE_RATE_MODE_WHISPER,
    SAMPLE_RATE_MODE_DEVICE,
    DEFAULT_SAMPLE_RATE_MODE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_BEAM_SIZE,
    DEFAULT_VAD_FILTER,
    DEFAULT_WORD_TIMESTAMPS,
    DEFAULT_SHORTCUT,
    DEFAULT_CLIPBOARD_DIAGNOSTICS,
)
from blaze.backends.registry import ModelRegistry
from blaze.backends.coordinator import get_coordinator
from blaze.backends.dependency_manager import DependencyManager
from blaze.system.resource_detector import detect_resources
import logging

logger = logging.getLogger(__name__)


class SettingsBridge(QObject):
    """Bridge between Python settings and QML interface."""

    # Signals to notify QML of changes
    settingChanged = pyqtSignal(str, "QVariant")
    modelDownloadProgress = pyqtSignal(str, int)  # model_name, progress_percent
    modelDownloadComplete = pyqtSignal(str)  # model_name
    modelDownloadError = pyqtSignal(str, str)  # model_name, error_message
    dependencyInstallProgress = pyqtSignal(
        str, str, int
    )  # backend, message, progress_percent
    dependencyInstallComplete = pyqtSignal(str, bool)  # backend, success
    backendAvailabilityChanged = pyqtSignal(str, bool)  # backend, available
    activeModelChanged = pyqtSignal(
        str
    )  # model_name - emitted when user selects new model

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    # === SVG path property ===

    @pyqtProperty(str)
    def svgPath(self):
        """Return the absolute path to syllablaze.svg for use as file:// URL in QML."""
        search_dirs = [
            os.path.join(os.path.dirname(__file__), "..", "resources"),
            os.path.join(os.path.dirname(__file__), "resources"),
            os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps"),
        ]
        for d in search_dirs:
            p = os.path.join(d, "syllablaze.svg")
            if os.path.exists(p):
                return os.path.abspath(p)
        return ""

    # === Generic get/set ===

    @pyqtSlot(str, result="QVariant")
    def get(self, key):
        """Get a setting value from Python."""
        value = self.settings.get(key)
        logger.debug(f"SettingsBridge.get({key}) = {value}")
        return value

    @pyqtSlot(str, "QVariant")
    def set(self, key, value):
        """Set a setting value from QML."""
        try:
            logger.info(f"SettingsBridge.set({key}, {value})")
            self.settings.set(key, value)
            self.settingChanged.emit(key, value)
        except Exception as e:
            logger.error(f"Failed to set {key}={value}: {e}")

    # === Audio settings ===

    @pyqtSlot(result=int)
    def getMicIndex(self):
        """Get saved microphone index. -1 means system default."""
        return self.settings.get("mic_index", -1)

    @pyqtSlot(int)
    def setMicIndex(self, index):
        self.set("mic_index", index)

    @pyqtSlot(result=str)
    def getSampleRateMode(self):
        return self.settings.get("sample_rate_mode", DEFAULT_SAMPLE_RATE_MODE)

    @pyqtSlot(str)
    def setSampleRateMode(self, mode):
        self.set("sample_rate_mode", mode)

    # === Transcription settings ===

    @pyqtSlot(result=str)
    def getLanguage(self):
        return self.settings.get("language", "auto")

    @pyqtSlot(str)
    def setLanguage(self, lang):
        self.set("language", lang)

    @pyqtSlot(result=str)
    def getComputeType(self):
        return self.settings.get("compute_type", DEFAULT_COMPUTE_TYPE)

    @pyqtSlot(str)
    def setComputeType(self, compute_type):
        self.set("compute_type", compute_type)

    @pyqtSlot(result=str)
    def getDevice(self):
        return self.settings.get("device", DEFAULT_DEVICE)

    @pyqtSlot(str)
    def setDevice(self, device):
        self.set("device", device)

    @pyqtSlot(result=int)
    def getBeamSize(self):
        return self.settings.get("beam_size", DEFAULT_BEAM_SIZE)

    @pyqtSlot(int)
    def setBeamSize(self, size):
        self.set("beam_size", size)

    @pyqtSlot(result=bool)
    def getVadFilter(self):
        return bool(self.settings.get("vad_filter", DEFAULT_VAD_FILTER))

    @pyqtSlot(bool)
    def setVadFilter(self, enabled):
        self.set("vad_filter", enabled)

    @pyqtSlot(result=bool)
    def getWordTimestamps(self):
        return bool(self.settings.get("word_timestamps", DEFAULT_WORD_TIMESTAMPS))

    @pyqtSlot(bool)
    def setWordTimestamps(self, enabled):
        self.set("word_timestamps", enabled)

    @pyqtSlot(result=bool)
    def getClipboardDiagnostics(self):
        return bool(
            self.settings.get("clipboard_diagnostics", DEFAULT_CLIPBOARD_DIAGNOSTICS)
        )

    @pyqtSlot(bool)
    def setClipboardDiagnostics(self, enabled):
        self.set("clipboard_diagnostics", enabled)

    # === Shortcuts ===

    @pyqtSlot(result=str)
    def getShortcut(self):
        """Get the active shortcut from kglobalaccel (KDE System Settings)."""
        try:
            # Read kglobalshortcutsrc file directly (sync, no D-Bus needed)
            import configparser
            from pathlib import Path

            config_path = Path.home() / ".config" / "kglobalshortcutsrc"
            logger.info(f"Reading shortcut from: {config_path}")

            if config_path.exists():
                config = configparser.ConfigParser()
                config.read(config_path)

                # Debug: log all sections
                logger.info(f"Available sections: {config.sections()}")

                # Look for Syllablaze shortcut
                if "org.kde.syllablaze" in config:
                    section = config["org.kde.syllablaze"]
                    logger.info(
                        f"Found syllablaze section, keys: {list(section.keys())}"
                    )

                    if "ToggleRecording" in section:
                        # Parse the shortcut entry
                        # Format: "active_shortcut,default_shortcut,description"
                        shortcut_entry = section["ToggleRecording"]
                        logger.info(f"Raw shortcut entry: {shortcut_entry}")

                        parts = shortcut_entry.split(",")
                        logger.info(f"Parsed parts: {parts}")

                        if len(parts) >= 1:
                            # First part is the active shortcut
                            active_shortcut = parts[0].strip()
                            if active_shortcut and active_shortcut.lower() != "none":
                                logger.info(f"Found active shortcut: {active_shortcut}")
                                return active_shortcut
                            else:
                                logger.info("Active shortcut is 'none', trying default")
                                # Try default shortcut (second part)
                                if len(parts) >= 2:
                                    default_shortcut = parts[1].strip()
                                    if (
                                        default_shortcut
                                        and default_shortcut.lower() != "none"
                                    ):
                                        logger.info(
                                            f"Using default shortcut: {default_shortcut}"
                                        )
                                        return default_shortcut
                else:
                    logger.warning(
                        "org.kde.syllablaze section not found in kglobalshortcutsrc"
                    )
            else:
                logger.warning(f"Config file not found: {config_path}")
        except Exception as e:
            logger.error(
                f"Failed to read shortcut from kglobalaccel: {e}", exc_info=True
            )

        # Fallback to QSettings
        shortcut = self.settings.get("shortcut", DEFAULT_SHORTCUT)
        logger.info(f"getShortcut() fallback to QSettings: {shortcut}")
        return shortcut if shortcut else DEFAULT_SHORTCUT

    # === Data providers ===

    @pyqtSlot(result="QVariantList")
    def getAvailableLanguages(self):
        """Get available languages as list of dicts for QML."""
        languages = []
        for code, name in Settings.VALID_LANGUAGES.items():
            languages.append({"code": code, "name": name})
        return languages

    # === Model Management (Multi-Backend) ===

    @pyqtSlot(str, str, result="QVariant")
    def getAvailableModels(self, language_filter="all", backend_filter="all"):
        """Get list of available models filtered by language and backend preference."""
        try:
            # Get system resources first
            try:
                resources = detect_resources()
                logger.info(
                    f"Detected resources: RAM={resources.total_ram_gb}GB total, "
                    f"{resources.available_ram_gb}GB available, "
                    f"GPU={'Yes' if resources.gpu_available else 'No'}"
                )
            except Exception as e:
                logger.error(f"Failed to detect resources: {e}")
                # Use default resources
                from blaze.system.resource_detector import SystemResources

                resources = SystemResources(
                    total_ram_gb=8.0,
                    available_ram_gb=4.0,
                    cpu_count=4,
                    gpu_available=False,
                    recommended_tier="light",
                )

            # Get current active model from settings
            current_model = self.settings.get("model", "whisper-tiny")
            logger.info(f"Current active model: {current_model}")

            # Determine which language to filter by
            # language_filter="all" means multilingual mode - show models that support all languages
            # language_filter="en", "fr", etc. means specific language - show models that support it
            target_language = (
                language_filter
                if language_filter and language_filter != "all"
                else None
            )
            logger.info(
                f"Language filter: {language_filter}, target_language: {target_language}"
            )

            # Get models filtered by language from the unified registry
            try:
                if target_language:
                    # Specific language selected - get models that support this language
                    models_to_check = ModelRegistry.get_models_for_language(
                        target_language
                    )
                else:
                    # Multilingual mode - show models that support "all" languages OR have 3+ languages
                    all_models = ModelRegistry.get_all_models()
                    models_to_check = []
                    for model in all_models:
                        # Include models with "all" in languages or with 3+ languages (multilingual)
                        if "all" in model.languages or len(model.languages) >= 3:
                            models_to_check.append(model)

                logger.info(
                    f"Found {len(models_to_check)} models from registry "
                    f"for language={target_language}, backend={backend_filter}"
                )
            except Exception as e:
                logger.error(f"Failed to get models from registry: {e}")
                # Fallback to all models from registry
                models_to_check = ModelRegistry.get_all_models()
                logger.info(
                    f"Falling back to all {len(models_to_check)} models from registry"
                )

            # Filter by backend if specified
            if backend_filter and backend_filter != "all":
                models_to_check = [
                    m for m in models_to_check if m.backend == backend_filter
                ]
                logger.info(
                    f"After backend filter '{backend_filter}': {len(models_to_check)} models"
                )
                # If filtering by a specific backend and no models found,
                # return empty list (don't fall back to other models)
                if not models_to_check:
                    logger.info(
                        f"No models found for backend '{backend_filter}' - returning empty list"
                    )
                    return []

            # Get coordinator for download status check (may fail if backends not available)
            coordinator = None
            try:
                coordinator = get_coordinator()
                logger.info("Successfully got coordinator")
            except Exception as e:
                logger.warning(f"Could not get coordinator for download status: {e}")

            models = []
            for model in models_to_check:
                try:
                    # Get compatibility info
                    compat = ModelRegistry.get_compatibility_info(
                        model.model_id,
                        resources.total_ram_gb,
                        resources.available_ram_gb,
                        resources.gpu_available,
                        resources.gpu_memory_gb,
                    )

                    # Check if model is downloaded (safely)
                    is_downloaded = False
                    if coordinator:
                        try:
                            is_downloaded = coordinator.is_model_downloaded(
                                model.model_id
                            )
                        except Exception as e:
                            logger.debug(
                                f"Could not check download status for {model.model_id}: {e}"
                            )

                    # Format size
                    if model.size_mb >= 1000:
                        size_str = f"{model.size_mb / 1024:.1f} GB"
                    else:
                        size_str = f"{model.size_mb} MB"

                    # Ensure all values are basic Python types for QML compatibility
                    model_dict = {
                        "id": str(model.model_id),
                        "name": str(model.name),
                        "backend": str(model.backend),
                        "description": str(model.description)
                        if model.description
                        else "",
                        "size": str(size_str),
                        "sizeMB": int(model.size_mb),
                        "downloaded": bool(is_downloaded),
                        "active": bool(model.model_id == current_model),
                        "compatible": bool(compat["compatible"]),
                        "compatibility_reason": str(compat["reason"])
                        if compat["reason"]
                        else "",
                        "recommended": bool(compat["recommended"]),
                        "languages": [str(lang) for lang in model.languages],
                        "tier": str(
                            model.tier.value
                            if hasattr(model.tier, "value")
                            else model.tier
                        ),
                    }
                    models.append(model_dict)
                except Exception as e:
                    logger.error(f"Error processing model {model.model_id}: {e}")
                    # Skip this model but continue with others
                    continue

            # Sort models: recommended first, then by performance (high to low), then by size (small to large)
            def get_model_performance(model_dict):
                """Get performance score for sorting."""
                try:
                    # Get the actual model to access language_performance
                    model = ModelRegistry.get_model(model_dict["id"])
                    if model and model.language_performance:
                        # Use "all" score if available, otherwise use first available language score
                        if "all" in model.language_performance:
                            return model.language_performance["all"]
                        elif model.language_performance:
                            return max(model.language_performance.values())
                except Exception:
                    pass
                # Fallback tier-based performance
                tier_scores = {
                    "ultra_light": 0.70,
                    "light": 0.80,
                    "medium": 0.88,
                    "heavy": 0.95,
                }
                return tier_scores.get(model_dict["tier"], 0.75)

            try:
                models.sort(
                    key=lambda m: (
                        not m[
                            "recommended"
                        ],  # Recommended first (False < True, so negate)
                        -get_model_performance(
                            m
                        ),  # Higher performance first (negate for descending)
                        m["sizeMB"],  # Smaller size first
                    )
                )
            except Exception as e:
                logger.error(f"Error sorting models: {e}")
                # Keep unsorted list

            logger.info(
                f"Returning {len(models)} models for language filter: {language_filter}"
            )

            if not models:
                logger.warning("No models found! This should not happen.")
                # Return legacy models as absolute fallback
                return self._getLegacyModels()

            return models

        except Exception as e:
            logger.error(f"Failed to get available models: {e}", exc_info=True)
            # Fallback to legacy implementation
            return self._getLegacyModels()

            return models

        except Exception as e:
            logger.error(f"Failed to get available models: {e}", exc_info=True)
            # Fallback to legacy implementation
            return self._getLegacyModels()

    def _getLegacyModels(self):
        """Legacy model list for backward compatibility - used when unified registry fails"""
        logger.info("Using legacy model list fallback")

        MODEL_SIZES = {
            "tiny": 75,
            "tiny.en": 75,
            "base": 145,
            "base.en": 145,
            "small": 485,
            "small.en": 485,
            "medium": 1500,
            "medium.en": 1500,
            "large-v1": 3100,
            "large-v2": 3100,
            "large-v3": 3100,
            "large-v3-turbo": 1600,
            "large": 3100,
            "distil-small.en": 340,
            "distil-medium.en": 790,
            "distil-large-v2": 1600,
            "distil-large-v3": 1600,
            "distil-large-v3.5": 1600,
        }

        MODEL_DESCRIPTIONS = {
            "tiny": "Fastest model, basic accuracy (75MB). Good for CPU-only systems.",
            "tiny.en": "English-only version of tiny model (75MB).",
            "base": "Good balance of speed and accuracy (145MB).",
            "base.en": "English-only version of base model (145MB).",
            "small": "Better accuracy, still fast (485MB).",
            "small.en": "English-only version of small model (485MB).",
            "medium": "High accuracy, multilingual (1.5GB).",
            "medium.en": "High accuracy, English-only (1.5GB).",
            "large-v1": "Excellent accuracy, large model (3.1GB).",
            "large-v2": "Excellent accuracy, large model (3.1GB).",
            "large-v3": "Best Whisper accuracy (3.1GB).",
            "large-v3-turbo": "Large v3 accuracy with faster inference (1.6GB).",
            "large": "Excellent accuracy, large model (3.1GB).",
            "distil-small.en": "Distilled for speed, English-only (340MB).",
            "distil-medium.en": "Distilled for speed, English-only (790MB).",
            "distil-large-v2": "Distilled large model (1.6GB).",
            "distil-large-v3": "Distilled large model (1.6GB).",
            "distil-large-v3.5": "Distilled large model (1.6GB).",
        }

        try:
            from blaze.models import WhisperModelManager

            manager = WhisperModelManager(self.settings)
            available_models = manager.AVAILABLE_MODELS
            logger.info(
                f"Legacy: Got {len(available_models)} models from WhisperModelManager"
            )
        except Exception as e:
            logger.error(f"Legacy: Could not get models from WhisperModelManager: {e}")
            # Hardcoded fallback
            available_models = list(MODEL_SIZES.keys())
            logger.info(
                f"Legacy: Using hardcoded list of {len(available_models)} models"
            )

        models = []
        current_model = self.settings.get("model", "whisper-tiny")

        # Map legacy model names to unified format for comparison
        def legacy_to_unified(name):
            return f"whisper-{name}" if not name.startswith("whisper-") else name

        for model_name in available_models:
            try:
                size_mb = MODEL_SIZES.get(model_name, 100)

                if size_mb >= 1000:
                    size_str = f"{size_mb / 1024:.1f} GB"
                else:
                    size_str = f"{size_mb} MB"

                # Check if downloaded (safely)
                is_downloaded = False
                try:
                    from blaze.models import WhisperModelManager

                    manager = WhisperModelManager(self.settings)
                    is_downloaded = manager.is_model_downloaded(model_name)
                except Exception as e:
                    logger.debug(
                        f"Could not check download status for {model_name}: {e}"
                    )

                unified_name = legacy_to_unified(model_name)

                models.append(
                    {
                        "id": unified_name,
                        "name": model_name.capitalize(),
                        "backend": "whisper",
                        "description": MODEL_DESCRIPTIONS.get(
                            model_name, f"{model_name} model"
                        ),
                        "size": size_str,
                        "sizeMB": size_mb,
                        "downloaded": is_downloaded,
                        "active": unified_name == current_model
                        or model_name == current_model,
                        "compatible": True,
                        "compatibility_reason": "",
                        "recommended": False,
                        "languages": ["all"] if ".en" not in model_name else ["en"],
                        "tier": "light" if size_mb < 1000 else "heavy",
                    }
                )
            except Exception as e:
                logger.error(f"Error processing legacy model {model_name}: {e}")
                continue

        logger.info(f"Legacy: Returning {len(models)} models")
        return models

    @pyqtSlot(result="QVariantMap")
    def getHardwareInfo(self):
        """Get system hardware information."""
        try:
            resources = detect_resources()
            return resources.to_dict()
        except Exception as e:
            logger.error(f"Failed to get hardware info: {e}")
            return {
                "total_ram_gb": 8.0,
                "available_ram_gb": 4.0,
                "cpu_count": 4,
                "gpu_available": False,
                "recommended_tier": "light",
                "error": str(e),
            }

    @pyqtSlot(result="QVariantMap")
    def getRecommendedModel(self):
        """Get the best model recommendation for current hardware."""
        try:
            from blaze.system.resource_detector import ResourceDetector

            detector = ResourceDetector()
            resources = detector.detect()
            language = self.settings.get("language")
            if language == "auto":
                language = None

            model = detector.get_best_model_for_system(ModelRegistry, language)

            if model:
                return {
                    "id": model.model_id,
                    "name": model.name,
                    "backend": model.backend,
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get recommended model: {e}")
            return {}

    @pyqtSlot(result=str)
    def getSystemLanguage(self):
        """Get the KDE system locale language code (e.g., 'en', 'fr', 'de')."""
        try:
            import locale
            import os

            # Try environment variables first (KDE sets these)
            lang_env = os.environ.get("LANG", "")
            if lang_env:
                # Extract language code from "en_GB.UTF-8" -> "en"
                lang_code = lang_env.split("_")[0].split(".")[0].lower()
                if lang_code in Settings.VALID_LANGUAGES and lang_code != "auto":
                    logger.info(f"Detected system language from LANG: {lang_code}")
                    return lang_code

            # Fallback to locale module
            try:
                loc = locale.getlocale()
                if loc and loc[0]:
                    lang_code = loc[0].split("_")[0].lower()
                    if lang_code in Settings.VALID_LANGUAGES and lang_code != "auto":
                        logger.info(
                            f"Detected system language from locale: {lang_code}"
                        )
                        return lang_code
            except:
                pass

            # Default to English
            logger.info("Could not detect system language, defaulting to 'en'")
            return "en"
        except Exception as e:
            logger.error(f"Failed to get system language: {e}")
            return "en"

    @pyqtSlot(result=bool)
    def getLanguageMultilingual(self):
        """Get whether multilingual mode is enabled."""
        return bool(self.settings.get("language_multilingual", True))

    @pyqtSlot(bool)
    def setLanguageMultilingual(self, enabled):
        """Set multilingual mode."""
        self.set("language_multilingual", enabled)
        # Emit signal to refresh models
        self.settingChanged.emit("language_mode_changed", enabled)

    @pyqtSlot(result=str)
    def getLanguageSpecific(self):
        """Get the specific language when not in multilingual mode."""
        # Default to system language if not set
        specific = self.settings.get("language_specific", None)
        if specific is None:
            specific = self.getSystemLanguage()
            self.settings.set("language_specific", specific)
        return specific

    @pyqtSlot(str)
    def setLanguageSpecific(self, lang_code):
        """Set the specific language code."""
        if lang_code in Settings.VALID_LANGUAGES and lang_code != "auto":
            self.set("language_specific", lang_code)
            # Emit signal to refresh models
            self.settingChanged.emit("language_mode_changed", lang_code)

    @pyqtSlot(str)
    def downloadModel(self, model_name):
        """Download a model with progress updates (supports new model_id format)."""
        import threading

        logger.info(f"Starting download of model: {model_name}")
        coordinator = get_coordinator()

        def progress_callback(progress):
            self.modelDownloadProgress.emit(model_name, int(progress))

        def download_thread():
            try:
                # Check if using new unified model_id format
                model_info = ModelRegistry.get_model(model_name)
                if model_info:
                    # New format
                    success = coordinator.download_model(model_name, progress_callback)
                else:
                    # Legacy format (e.g., "tiny", "base")
                    from blaze.models import WhisperModelManager

                    manager = WhisperModelManager(self.settings)
                    manager.download_model(
                        model_name, progress_callback=progress_callback
                    )
                    success = True

                if success:
                    self.modelDownloadComplete.emit(model_name)
                    logger.info(f"Model download complete: {model_name}")
                else:
                    self.modelDownloadError.emit(model_name, "Download failed")
            except Exception as e:
                error_msg = str(e)
                self.modelDownloadError.emit(model_name, error_msg)
                logger.error(f"Model download failed: {model_name} - {error_msg}")

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    @pyqtSlot(str)
    def deleteModel(self, model_name):
        """Delete a model (supports new model_id format)."""
        try:
            logger.info(f"Deleting model: {model_name}")
            coordinator = get_coordinator()

            # Check if using new unified model_id format
            model_info = ModelRegistry.get_model(model_name)
            if model_info:
                # New format
                coordinator.delete_model(model_name)
            else:
                # Legacy format
                from blaze.models import WhisperModelManager

                manager = WhisperModelManager(self.settings)
                manager.delete_model(model_name)

            logger.info(f"Model deleted successfully: {model_name}")
        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            self.modelDownloadError.emit(model_name, str(e))

    @pyqtSlot(str)
    def setActiveModel(self, model_name):
        """Set the active model.

        Note: Backend type is now derived from model_id at runtime
        in TranscriptionManager, so we no longer store model_backend.
        This prevents stale backend information when switching models.

        Emits activeModelChanged signal to trigger hard reset in main app.
        """
        logger.info(f"Setting active model: {model_name}")

        # Store the model name - backend will be derived from model_id
        self.set("model", model_name)

        # Log the backend type for debugging (but don't store it)
        try:
            from blaze.backends.registry import ModelRegistry

            model_info = ModelRegistry.get_model(model_name)
            if model_info:
                logger.info(f"Model {model_name} uses backend '{model_info.backend}'")
            else:
                logger.warning(
                    f"Model {model_name} not found in registry, will default to whisper"
                )
        except Exception as e:
            logger.error(f"Failed to get model backend info: {e}")

        # Emit signal to notify main app that model changed
        # This triggers a hard reset - stopping any ongoing transcription
        self.activeModelChanged.emit(model_name)

    def _check_model_downloaded_safe(self, coordinator, model_id):
        """Safely check if model is downloaded, returning False on any error."""
        try:
            if coordinator:
                return coordinator.is_model_downloaded(model_id)
        except Exception as e:
            logger.debug(f"Could not check download status for {model_id}: {e}")
        return False

    @pyqtSlot(str, result="QVariantMap")
    def getModelDetails(self, model_id):
        """Get detailed information about a specific model for the popup."""
        try:
            coordinator = get_coordinator()
            current_model = self.settings.get("model", "whisper-tiny")

            model = ModelRegistry.get_model(model_id)
            if not model:
                return {"error": f"Model not found: {model_id}"}

            # Get compatibility info
            resources = detect_resources()
            compat = ModelRegistry.get_compatibility_info(
                model.model_id,
                resources.total_ram_gb,
                resources.available_ram_gb,
                resources.gpu_available,
                resources.gpu_memory_gb,
            )

            # Format GPU preference for display
            gpu_pref_map = {
                "gpu_agnostic": "Works on CPU or GPU",
                "gpu_preferred": "Works best with GPU",
                "nvidia_preferred": "Optimized for NVIDIA GPUs",
            }
            gpu_preference_display = gpu_pref_map.get(
                model.gpu_preference, model.gpu_preference
            )

            # Build language performance display
            lang_perf = {}
            if model.language_performance:
                for lang, score in model.language_performance.items():
                    if lang == "all":
                        lang_perf["Multilingual"] = f"{int(score * 100)}%"
                    elif lang in Settings.VALID_LANGUAGES:
                        lang_perf[Settings.VALID_LANGUAGES[lang]] = (
                            f"{int(score * 100)}%"
                        )
                    else:
                        lang_perf[lang.upper()] = f"{int(score * 100)}%"

            # Format languages list
            languages_display = []
            for lang in model.languages:
                if lang == "all":
                    languages_display.append("All languages")
                elif lang in Settings.VALID_LANGUAGES:
                    languages_display.append(Settings.VALID_LANGUAGES[lang])
                else:
                    languages_display.append(lang.upper())

            # Format size
            if model.size_mb >= 1000:
                size_str = f"{model.size_mb / 1024:.1f} GB"
            else:
                size_str = f"{model.size_mb} MB"

            return {
                "id": model.model_id,
                "name": model.name,
                "backend": model.backend,
                "description": model.description,
                "size": size_str,
                "size_mb": model.size_mb,
                "min_ram_gb": model.min_ram_gb,
                "recommended_ram_gb": model.recommended_ram_gb,
                "min_vram_gb": model.min_vram_gb,
                "languages": languages_display,
                "language_performance": lang_perf,
                "gpu_preference": gpu_preference_display,
                "gpu_preference_raw": model.gpu_preference,
                "tier": model.tier.value,
                "license": model.license,
                "supports_word_timestamps": model.supports_word_timestamps,
                "is_streaming": model.is_streaming,
                "compatible": compat["compatible"],
                "compatibility_reason": compat["reason"],
                "recommended": compat["recommended"],
                "downloaded": self._check_model_downloaded_safe(
                    coordinator, model.model_id
                ),
                "active": model.model_id == current_model,
            }
        except Exception as e:
            logger.error(f"Failed to get model details for {model_id}: {e}")
            return {"error": str(e)}

    @pyqtSlot(result="QVariantMap")
    def getLiquidSettings(self):
        """Get Liquid backend generation settings."""
        return {
            "temperature": self.settings.get("liquid_temperature", 0.3),
            "top_k": self.settings.get("liquid_top_k", 50),
            "max_tokens": self.settings.get("liquid_max_tokens", 200),
        }

    @pyqtSlot(float)
    def setLiquidTemperature(self, value):
        """Set Liquid generation temperature (0.0-1.0)."""
        if 0.0 <= value <= 1.0:
            self.settings.set("liquid_temperature", value)
            logger.info(f"Liquid temperature set to {value}")

    @pyqtSlot(int)
    def setLiquidTopK(self, value):
        """Set Liquid top-k sampling value."""
        if 1 <= value <= 100:
            self.settings.set("liquid_top_k", value)
            logger.info(f"Liquid top_k set to {value}")

    @pyqtSlot(int)
    def setLiquidMaxTokens(self, value):
        """Set Liquid max tokens to generate."""
        if 10 <= value <= 500:
            self.settings.set("liquid_max_tokens", value)
            logger.info(f"Liquid max_tokens set to {value}")

    # === Dependency Management Methods ===

    @pyqtSlot(str, result="QVariantMap")
    def getBackendDependencyInfo(self, backend):
        """Get dependency information for a backend."""
        try:
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
        except Exception as e:
            logger.error(f"Failed to get backend info for {backend}: {e}")
            return {"available": False, "error": str(e)}

    @pyqtSlot(str, result=bool)
    def checkBackendDependencies(self, backend):
        """Check if a backend's dependencies are installed."""
        try:
            return DependencyManager.is_backend_available(backend)
        except Exception as e:
            logger.error(f"Failed to check backend dependencies: {e}")
            return False

    @pyqtSlot(str)
    def installBackendDependencies(self, backend):
        """Install dependencies for a backend."""
        import threading

        def progress_callback(message, progress):
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

    @pyqtSlot(result="QVariantList")
    def getAllBackendsWithStatus(self):
        """Get all backends with their availability status."""
        try:
            result = []
            all_backends = ["whisper", "liquid", "qwen"]

            for backend in all_backends:
                info = DependencyManager.get_backend_info(backend)
                if info:
                    result.append(
                        {
                            "name": backend,
                            "available": DependencyManager.is_backend_available(
                                backend
                            ),
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
        except Exception as e:
            logger.error(f"Failed to get all backends: {e}")
            return []

    @pyqtSlot(str, result="QVariant")
    def getBackendForModel(self, model_id):
        """Get the backend name for a specific model."""
        try:
            model = ModelRegistry.get_model(model_id)
            if model:
                return model.backend
            return None
        except Exception as e:
            logger.error(f"Failed to get backend for model {model_id}: {e}")
            return None

    @pyqtSlot(str, result=bool)
    def canDownloadModel(self, model_id):
        """Check if a model can be downloaded (backend available)."""
        try:
            coordinator = get_coordinator()
            model = ModelRegistry.get_model(model_id)
            if not model:
                return False
            return coordinator.is_backend_available(model.backend)
        except Exception as e:
            logger.error(f"Failed to check if model can be downloaded: {e}")
            return False

    @pyqtSlot(result="QVariantList")
    def getAudioDevices(self):
        """Get audio input devices via PyAudio with blocklist filtering."""
        devices = []

        # Blocklist patterns for non-microphone devices
        # Based on research of PulseAudio, PipeWire, and ALSA naming conventions
        skip_patterns = [
            # Audio servers and virtual devices
            "pulse",
            "pulseaudio",
            "jack",
            "pipewire",
            "pipe wire",
            # Virtual/loopback devices
            "virtual",
            "loopback",
            "dummy",
            "null",
            # ALSA virtual/default devices
            "sysdefault",
            "default",
            "dmix",
            "dsnoop",
            # ALSA rate converters and codecs
            "lavrate",
            "samplerate",
            "speexrate",
            "speex",
            # Monitor devices (CRITICAL - most common false positive)
            ".monitor",
            "monitor of",
            "monitor for",
            # System/Desktop audio capture
            "stereo mix",
            "what u hear",
            "desktop",
            "system",
            # Echo cancellation and filters
            "echo",
            "echo-cancel",
            "filter",
            # Mixers and routing
            "mix",
            "mixer",
            "up mix",
            "down mix",
            "mix down",
            "remap",
            # Digital audio interfaces (outputs, not inputs)
            "spdif",
            "s/pdif",
            "iec958",
            "aes",
            "aes3",
            "s/pdif optical",
            # Video device audio (usually HDMI/DP outputs)
            "hdmi",
            "displayport",
            "dp audio",
            "usb video",
            # Output devices
            "speaker",
            "headphone",
            "output",
            "analog stereo",
            # Split/duplicate channels
            "split",
            # Browser audio capture
            "browser",
        ]

        try:
            import pyaudio

            pa = pyaudio.PyAudio()
            try:
                device_count = pa.get_device_count()
                logger.info("=" * 60)
                logger.info("ENUMERATING ALL AUDIO DEVICES:")
                logger.info("=" * 60)

                for i in range(device_count):
                    try:
                        info = pa.get_device_info_by_index(i)
                    except Exception:
                        continue

                    device_name_original = str(info.get("name", f"Device {i}"))
                    max_input_channels = info.get("maxInputChannels", 0)
                    max_output_channels = info.get("maxOutputChannels", 0)

                    logger.info(f"Device {i}: '{device_name_original}'")
                    logger.info(
                        f"  Input channels: {max_input_channels}, Output channels: {max_output_channels}"
                    )

                    # Must have input channels
                    if (
                        not isinstance(max_input_channels, int)
                        or max_input_channels <= 0
                    ):
                        logger.info(f"  ❌ SKIPPED: No input channels")
                        continue

                    device_name = device_name_original.lower()

                    # Check each pattern
                    matched_pattern = None
                    for pattern in skip_patterns:
                        if pattern in device_name:
                            matched_pattern = pattern
                            break

                    if matched_pattern:
                        logger.info(
                            f"  ❌ SKIPPED: Matched pattern '{matched_pattern}'"
                        )
                        continue

                    # Device passed all filters - add it
                    devices.append({"name": device_name_original, "index": i})
                    logger.info(f"  ✅ KEPT: Added as microphone")

            finally:
                logger.info("=" * 60)
                logger.info(
                    f"SUMMARY: Kept {len(devices)} device(s) out of {device_count}"
                )
                logger.info("=" * 60)
                pa.terminate()

        except Exception as e:
            logger.error(f"Failed to enumerate audio devices: {e}")
            # Return placeholder on error
            return [{"name": "Default Microphone", "index": -1}]

        # If no devices found, return system default only
        if not devices:
            logger.warning("No microphone devices found, using system default")
            return [{"name": "System Default", "index": -1}]

        # Prepend system default as first option
        devices.insert(0, {"name": "System Default", "index": -1})
        logger.info(f"Found {len(devices) - 1} microphone device(s) + system default")
        return devices


class ActionsBridge(QObject):
    """Bridge for actions that QML can trigger."""

    def __init__(self):
        super().__init__()

    @pyqtSlot(str)
    def openUrl(self, url):
        """Open a URL in the default browser."""
        logger.info(f"Opening URL: {url}")
        QDesktopServices.openUrl(QUrl(url))

    @pyqtSlot()
    def openSystemSettings(self):
        """Open KDE System Settings (general)."""
        from PyQt6.QtCore import QProcess

        logger.info("Opening KDE System Settings")

        # Try systemsettings (KDE 6) first
        success = QProcess.startDetached("systemsettings")
        if success:
            logger.info("Successfully launched systemsettings")
        else:
            # Fallback to systemsettings5 (KDE 5)
            logger.warning("systemsettings failed, trying systemsettings5")
            QProcess.startDetached("systemsettings5")

    @pyqtSlot()
    def openShortcutSettings(self):
        """Open KDE System Settings directly to Syllablaze shortcut configuration."""
        from PyQt6.QtCore import QProcess

        logger.info("=" * 60)
        logger.info("openShortcutSettings() called from QML")
        logger.info("Launching: kcmshell6 kcm_keys --args Syllablaze")
        logger.info("=" * 60)

        # Try kcmshell6 first (KDE 6)
        success = QProcess.startDetached(
            "kcmshell6", ["kcm_keys", "--args", "Syllablaze"]
        )
        if success:
            logger.info("Successfully launched kcmshell6")
        else:
            # Fallback to systemsettings with shortcuts page
            logger.warning("kcmshell6 failed, trying systemsettings")
            QProcess.startDetached("systemsettings", ["kcm_keys"])


class KirigamiSettingsWindow(QWidget):
    """Kirigami-based settings window that replaces PyQt6 SettingsWindow."""

    initialization_complete = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.whisper_model = None
        self.current_model = None

        self.setWindowTitle(f"{APP_NAME} Settings")
        # Window size is managed by QML based on screen resolution

        # Create bridges
        self.settings_bridge = SettingsBridge(settings)
        self.actions_bridge = ActionsBridge()

        # Use QQmlApplicationEngine for reliable QML loading
        self.engine = QQmlApplicationEngine()

        # Add Qt6 QML module path for Kirigami
        self.engine.addImportPath("/usr/lib/qt6/qml")

        # Debug: Log import paths
        logger.info(f"QML Import Paths: {self.engine.importPathList()}")

        # Register bridges with QML context
        root_context = self.engine.rootContext()
        if root_context:
            root_context.setContextProperty("settingsBridge", self.settings_bridge)
            root_context.setContextProperty("actionsBridge", self.actions_bridge)
            root_context.setContextProperty("APP_NAME", APP_NAME)
            root_context.setContextProperty("APP_VERSION", APP_VERSION)
            root_context.setContextProperty("GITHUB_REPO_URL", GITHUB_REPO_URL)

        # Load Kirigami settings window
        qml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "qml/SyllablazeSettings.qml"
        )
        logger.info(f"Loading QML from: {qml_path}")
        self.engine.load(QUrl.fromLocalFile(qml_path))

        # Store the root object
        root_objects = self.engine.rootObjects()
        if root_objects:
            self.root_window = root_objects[0]

            # Set window flags to make it a proper standalone window
            if hasattr(self.root_window, "setFlags"):
                from PyQt6.QtCore import Qt

                self.root_window.setFlags(
                    Qt.WindowType.Window
                    | Qt.WindowType.WindowCloseButtonHint
                    | Qt.WindowType.WindowMinimizeButtonHint
                    | Qt.WindowType.WindowMaximizeButtonHint
                )
                logger.info("Set window flags for standalone display")

            # Create KWin rule to prevent settings window from being on all desktops
            # (unlike recording applet, settings should stay on current desktop)
            try:
                from blaze import kwin_rules

                kwin_rules.create_settings_window_rule()
                logger.info("Created KWin rule for settings window")
            except Exception as e:
                logger.warning(f"Failed to create settings window KWin rule: {e}")

            logger.info("Kirigami SettingsWindow loaded successfully")
        else:
            logger.error("Failed to load Kirigami SettingsWindow")
            # Print QML errors
            for error in self.engine.rootObjects():
                logger.error(f"QML Error: {error}")

    def show(self):
        """Show the Kirigami settings window."""
        if hasattr(self, "root_window") and self.root_window:
            logger.info(
                f"Showing Kirigami window (current visibility: {self.root_window.isVisible() if hasattr(self.root_window, 'isVisible') else 'unknown'})"
            )

            # Set visibility explicitly
            if hasattr(self.root_window, "setVisible"):
                self.root_window.setVisible(True)

            # Show the QML window
            self.root_window.show()

            # Raise and activate to bring to front
            if hasattr(self.root_window, "raise_"):
                self.root_window.raise_()
            if hasattr(self.root_window, "requestActivate"):
                self.root_window.requestActivate()

            # Center the window
            primary_screen = QApplication.primaryScreen()
            if primary_screen:
                screen = primary_screen.availableGeometry()
                self.root_window.setX(
                    screen.center().x() - self.root_window.width() // 2
                )
                self.root_window.setY(
                    screen.center().y() - self.root_window.height() // 2
                )

            logger.info(
                f"Window shown. New visibility: {self.root_window.isVisible() if hasattr(self.root_window, 'isVisible') else 'unknown'}, geometry: {self.root_window.width()}x{self.root_window.height()} at ({self.root_window.x()}, {self.root_window.y()})"
            )
        else:
            logger.error("Cannot show: No QML window loaded")

    def hide(self):
        """Hide the Kirigami settings window."""
        if hasattr(self, "root_window") and self.root_window:
            self.root_window.hide()

    def isVisible(self):
        """Check if the Kirigami settings window is visible."""
        if hasattr(self, "root_window") and self.root_window:
            return self.root_window.isVisible()
        return False

    def raise_(self):
        """Raise the Kirigami settings window."""
        if hasattr(self, "root_window") and self.root_window:
            self.root_window.raise_()

    def activateWindow(self):
        """Activate the Kirigami settings window."""
        if hasattr(self, "root_window") and self.root_window:
            if hasattr(self.root_window, "requestActivate"):
                self.root_window.requestActivate()
            else:
                self.root_window.raise_()

    def on_model_activated(self, model_name):
        """Handle model activation - emit initialization_complete signal."""
        if hasattr(self, "current_model") and model_name == self.current_model:
            return

        try:
            self.settings.set("model", model_name)
            self.current_model = model_name
            self.initialization_complete.emit()
        except Exception as e:
            logger.error(f"Failed to set model: {e}")


def show_kirigami_settings():
    """Display Kirigami settings window (for testing)."""
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QCoreApplication

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = QApplication(sys.argv)

    # Use separate settings namespace for testing to avoid affecting running app
    QCoreApplication.setOrganizationName("KDE-Testing")
    QCoreApplication.setApplicationName("Syllablaze-Kirigami-Test")

    logger.info("=" * 60)
    logger.info("KIRIGAMI TEST MODE - Using isolated settings")
    logger.info("This will NOT affect your running Syllablaze instance")
    logger.info("=" * 60)

    # Create a test settings instance for isolated testing
    test_settings = Settings()
    window = KirigamiSettingsWindow(test_settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    # Test Kirigami settings window
    show_kirigami_settings()
