"""
Kirigami Integration Layer for Syllablaze

This module replaces PyQt6 SettingsWindow with Kirigami QML interface.
"""

import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, Qt
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
)
import logging

logger = logging.getLogger(__name__)


class SettingsBridge(QObject):
    """Bridge between Python settings and QML interface."""

    # Signals to notify QML of changes
    settingChanged = pyqtSignal(str, 'QVariant')
    modelDownloadProgress = pyqtSignal(str, int)  # model_name, progress_percent
    modelDownloadComplete = pyqtSignal(str)  # model_name
    modelDownloadError = pyqtSignal(str, str)  # model_name, error_message

    def __init__(self):
        super().__init__()
        self.settings = Settings()

    # === Generic get/set ===

    @pyqtSlot(str, result='QVariant')
    def get(self, key):
        """Get a setting value from Python."""
        value = self.settings.get(key)
        logger.debug(f"SettingsBridge.get({key}) = {value}")
        return value

    @pyqtSlot(str, 'QVariant')
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
        return self.settings.get('mic_index', -1)

    @pyqtSlot(int)
    def setMicIndex(self, index):
        self.set('mic_index', index)

    @pyqtSlot(result=str)
    def getSampleRateMode(self):
        return self.settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)

    @pyqtSlot(str)
    def setSampleRateMode(self, mode):
        self.set('sample_rate_mode', mode)

    # === Transcription settings ===

    @pyqtSlot(result=str)
    def getLanguage(self):
        return self.settings.get('language', 'auto')

    @pyqtSlot(str)
    def setLanguage(self, lang):
        self.set('language', lang)

    @pyqtSlot(result=str)
    def getComputeType(self):
        return self.settings.get('compute_type', DEFAULT_COMPUTE_TYPE)

    @pyqtSlot(str)
    def setComputeType(self, compute_type):
        self.set('compute_type', compute_type)

    @pyqtSlot(result=str)
    def getDevice(self):
        return self.settings.get('device', DEFAULT_DEVICE)

    @pyqtSlot(str)
    def setDevice(self, device):
        self.set('device', device)

    @pyqtSlot(result=int)
    def getBeamSize(self):
        return self.settings.get('beam_size', DEFAULT_BEAM_SIZE)

    @pyqtSlot(int)
    def setBeamSize(self, size):
        self.set('beam_size', size)

    @pyqtSlot(result=bool)
    def getVadFilter(self):
        return self.settings.get('vad_filter', DEFAULT_VAD_FILTER)

    @pyqtSlot(bool)
    def setVadFilter(self, enabled):
        self.set('vad_filter', enabled)

    @pyqtSlot(result=bool)
    def getWordTimestamps(self):
        return self.settings.get('word_timestamps', DEFAULT_WORD_TIMESTAMPS)

    @pyqtSlot(bool)
    def setWordTimestamps(self, enabled):
        self.set('word_timestamps', enabled)

    # === Shortcuts ===

    @pyqtSlot(result=str)
    def getShortcut(self):
        """Get the active shortcut from kglobalaccel (KDE System Settings)."""
        try:
            # Read kglobalshortcutsrc file directly (sync, no D-Bus needed)
            import configparser
            from pathlib import Path

            config_path = Path.home() / '.config' / 'kglobalshortcutsrc'
            logger.info(f"Reading shortcut from: {config_path}")

            if config_path.exists():
                config = configparser.ConfigParser()
                config.read(config_path)

                # Debug: log all sections
                logger.info(f"Available sections: {config.sections()}")

                # Look for Syllablaze shortcut
                if 'org.kde.syllablaze' in config:
                    section = config['org.kde.syllablaze']
                    logger.info(f"Found syllablaze section, keys: {list(section.keys())}")

                    if 'ToggleRecording' in section:
                        # Parse the shortcut entry
                        # Format: "active_shortcut,default_shortcut,description"
                        shortcut_entry = section['ToggleRecording']
                        logger.info(f"Raw shortcut entry: {shortcut_entry}")

                        parts = shortcut_entry.split(',')
                        logger.info(f"Parsed parts: {parts}")

                        if len(parts) >= 1:
                            # First part is the active shortcut
                            active_shortcut = parts[0].strip()
                            if active_shortcut and active_shortcut.lower() != 'none':
                                logger.info(f"Found active shortcut: {active_shortcut}")
                                return active_shortcut
                            else:
                                logger.info("Active shortcut is 'none', trying default")
                                # Try default shortcut (second part)
                                if len(parts) >= 2:
                                    default_shortcut = parts[1].strip()
                                    if default_shortcut and default_shortcut.lower() != 'none':
                                        logger.info(f"Using default shortcut: {default_shortcut}")
                                        return default_shortcut
                else:
                    logger.warning("org.kde.syllablaze section not found in kglobalshortcutsrc")
            else:
                logger.warning(f"Config file not found: {config_path}")
        except Exception as e:
            logger.error(f"Failed to read shortcut from kglobalaccel: {e}", exc_info=True)

        # Fallback to QSettings
        shortcut = self.settings.get('shortcut', DEFAULT_SHORTCUT)
        logger.info(f"getShortcut() fallback to QSettings: {shortcut}")
        return shortcut if shortcut else DEFAULT_SHORTCUT

    # === Data providers ===

    @pyqtSlot(result='QVariantList')
    def getAvailableLanguages(self):
        """Get available languages as list of dicts for QML."""
        languages = []
        for code, name in Settings.VALID_LANGUAGES.items():
            languages.append({"code": code, "name": name})
        return languages

    # === Model Management ===

    @pyqtSlot(result='QVariantList')
    def getAvailableModels(self):
        """Get list of all available Whisper models with download status."""
        from blaze.utils.whisper_model_manager import WhisperModelManager
        import os

        # Approximate model sizes in MB (for display purposes)
        MODEL_SIZES = {
            "tiny": 75, "tiny.en": 75,
            "base": 145, "base.en": 145,
            "small": 485, "small.en": 485,
            "medium": 1500, "medium.en": 1500,
            "large-v1": 3100, "large-v2": 3100, "large-v3": 3100,
            "large-v3-turbo": 1600, "large": 3100,
            "distil-small.en": 340, "distil-medium.en": 790,
            "distil-large-v2": 1600, "distil-large-v3": 1600,
            "distil-large-v3.5": 1600,
        }

        manager = WhisperModelManager(self.settings)
        models = []
        current_model = self.settings.get('model', 'large-v3')

        for model_name in manager.AVAILABLE_MODELS:
            is_downloaded = manager.is_model_downloaded(model_name)

            # Get actual size if downloaded, otherwise use approximate
            size_mb = MODEL_SIZES.get(model_name, 0)
            logger.info(f"Model '{model_name}': initial size_mb={size_mb}, downloaded={is_downloaded}")

            if size_mb == 0:
                logger.warning(f"No size found in MODEL_SIZES for model: '{model_name}'")

            if is_downloaded:
                model_path = manager.get_model_path(model_name)
                logger.info(f"Model '{model_name}': model_path={model_path}")
                if model_path and os.path.exists(model_path):
                    try:
                        # Calculate actual size (handle both files and directories)
                        total_size = 0
                        if os.path.isfile(model_path):
                            # Single file (e.g., original Whisper .pt files)
                            total_size = os.path.getsize(model_path)
                        elif os.path.isdir(model_path):
                            # Directory (e.g., Faster Whisper model directories)
                            for dirpath, dirnames, filenames in os.walk(model_path):
                                for filename in filenames:
                                    filepath = os.path.join(dirpath, filename)
                                    total_size += os.path.getsize(filepath)
                        size_mb = int(total_size / (1024 * 1024))
                        logger.info(f"Model '{model_name}': calculated actual size={size_mb} MB from {total_size} bytes")
                    except Exception as e:
                        logger.warning(f"Model '{model_name}': failed to calculate size, keeping approximate: {e}")
                        pass  # Use approximate size on error

            # Format size for display
            if size_mb >= 1000:
                size_str = f"{size_mb / 1024:.1f} GB"
            else:
                size_str = f"{size_mb} MB"

            models.append({
                "name": model_name,
                "downloaded": is_downloaded,
                "active": model_name == current_model,
                "size": size_str,
                "sizeMB": size_mb
            })

        logger.info(f"Found {len(models)} available models")
        return models

    @pyqtSlot(str)
    def downloadModel(self, model_name):
        """Download a Whisper model with progress updates."""
        from blaze.utils.whisper_model_manager import WhisperModelManager
        import threading

        logger.info(f"Starting download of model: {model_name}")
        manager = WhisperModelManager(self.settings)

        def progress_callback(progress):
            self.modelDownloadProgress.emit(model_name, int(progress))

        def download_thread():
            try:
                manager.download_model(model_name, progress_callback=progress_callback)
                self.modelDownloadComplete.emit(model_name)
                logger.info(f"Model download complete: {model_name}")
            except Exception as e:
                error_msg = str(e)
                self.modelDownloadError.emit(model_name, error_msg)
                logger.error(f"Model download failed: {model_name} - {error_msg}")

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    @pyqtSlot(str)
    def deleteModel(self, model_name):
        """Delete a Whisper model."""
        from blaze.utils.whisper_model_manager import WhisperModelManager

        try:
            logger.info(f"Deleting model: {model_name}")
            manager = WhisperModelManager(self.settings)
            manager.delete_model(model_name)
            logger.info(f"Model deleted successfully: {model_name}")
        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            self.modelDownloadError.emit(model_name, str(e))

    @pyqtSlot(str)
    def setActiveModel(self, model_name):
        """Set the active Whisper model."""
        logger.info(f"Setting active model: {model_name}")
        self.set('model', model_name)

    @pyqtSlot(result='QVariantList')
    def getAudioDevices(self):
        """Get audio input devices via PyAudio with blocklist filtering."""
        devices = []

        # Blocklist patterns for non-microphone devices
        # Based on research of PulseAudio, PipeWire, and ALSA naming conventions
        skip_patterns = [
            # Audio servers and virtual devices
            "pulse", "pulseaudio", "jack", "pipewire", "pipe wire",
            # Virtual/loopback devices
            "virtual", "loopback", "dummy", "null",
            # ALSA virtual/default devices
            "sysdefault", "default", "dmix", "dsnoop",
            # ALSA rate converters and codecs
            "lavrate", "samplerate", "speexrate", "speex",
            # Monitor devices (CRITICAL - most common false positive)
            ".monitor", "monitor of", "monitor for",
            # System/Desktop audio capture
            "stereo mix", "what u hear", "desktop", "system",
            # Echo cancellation and filters
            "echo", "echo-cancel", "filter",
            # Mixers and routing
            "mix", "mixer", "up mix", "down mix", "mix down", "remap",
            # Digital audio interfaces (outputs, not inputs)
            "spdif", "s/pdif", "iec958", "aes", "aes3", "s/pdif optical",
            # Video device audio (usually HDMI/DP outputs)
            "hdmi", "displayport", "dp audio", "usb video",
            # Output devices
            "speaker", "headphone", "output", "analog stereo",
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
                    logger.info(f"  Input channels: {max_input_channels}, Output channels: {max_output_channels}")

                    # Must have input channels
                    if not isinstance(max_input_channels, int) or max_input_channels <= 0:
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
                        logger.info(f"  ❌ SKIPPED: Matched pattern '{matched_pattern}'")
                        continue

                    # Device passed all filters - add it
                    devices.append({
                        "name": device_name_original,
                        "index": i
                    })
                    logger.info(f"  ✅ KEPT: Added as microphone")

            finally:
                logger.info("=" * 60)
                logger.info(f"SUMMARY: Kept {len(devices)} device(s) out of {device_count}")
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
        logger.info(f"Found {len(devices)-1} microphone device(s) + system default")
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
        success = QProcess.startDetached("kcmshell6", ["kcm_keys", "--args", "Syllablaze"])
        if success:
            logger.info("Successfully launched kcmshell6")
        else:
            # Fallback to systemsettings with shortcuts page
            logger.warning("kcmshell6 failed, trying systemsettings")
            QProcess.startDetached("systemsettings", ["kcm_keys"])


class KirigamiSettingsWindow(QWidget):
    """Kirigami-based settings window that replaces PyQt6 SettingsWindow."""

    initialization_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.whisper_model = None
        self.current_model = None

        self.setWindowTitle(f"{APP_NAME} Settings")
        # Window size is managed by QML based on screen resolution

        # Create bridges
        self.settings_bridge = SettingsBridge()
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
            os.path.dirname(os.path.abspath(__file__)),
            "qml/SyllablazeSettings.qml"
        )
        logger.info(f"Loading QML from: {qml_path}")
        self.engine.load(QUrl.fromLocalFile(qml_path))

        # Store the root object
        root_objects = self.engine.rootObjects()
        if root_objects:
            self.root_window = root_objects[0]

            # Set window flags to make it a proper standalone window
            if hasattr(self.root_window, 'setFlags'):
                from PyQt6.QtCore import Qt
                self.root_window.setFlags(
                    Qt.WindowType.Window |
                    Qt.WindowType.WindowCloseButtonHint |
                    Qt.WindowType.WindowMinimizeButtonHint |
                    Qt.WindowType.WindowMaximizeButtonHint
                )
                logger.info("Set window flags for standalone display")

            logger.info("Kirigami SettingsWindow loaded successfully")
        else:
            logger.error("Failed to load Kirigami SettingsWindow")
            # Print QML errors
            for error in self.engine.rootObjects():
                logger.error(f"QML Error: {error}")

    def show(self):
        """Show the Kirigami settings window."""
        if hasattr(self, "root_window") and self.root_window:
            logger.info(f"Showing Kirigami window (current visibility: {self.root_window.isVisible() if hasattr(self.root_window, 'isVisible') else 'unknown'})")

            # Set visibility explicitly
            if hasattr(self.root_window, 'setVisible'):
                self.root_window.setVisible(True)

            # Show the QML window
            self.root_window.show()

            # Raise and activate to bring to front
            if hasattr(self.root_window, 'raise_'):
                self.root_window.raise_()
            if hasattr(self.root_window, 'requestActivate'):
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

            logger.info(f"Window shown. New visibility: {self.root_window.isVisible() if hasattr(self.root_window, 'isVisible') else 'unknown'}, geometry: {self.root_window.width()}x{self.root_window.height()} at ({self.root_window.x()}, {self.root_window.y()})")
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
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    app = QApplication(sys.argv)

    # Use separate settings namespace for testing to avoid affecting running app
    QCoreApplication.setOrganizationName("KDE-Testing")
    QCoreApplication.setApplicationName("Syllablaze-Kirigami-Test")

    logger.info("=" * 60)
    logger.info("KIRIGAMI TEST MODE - Using isolated settings")
    logger.info("This will NOT affect your running Syllablaze instance")
    logger.info("=" * 60)

    window = KirigamiSettingsWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    # Test Kirigami settings window
    show_kirigami_settings()
