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
        shortcut = self.settings.get('shortcut', DEFAULT_SHORTCUT)
        logger.debug(f"getShortcut() returning: {shortcut}")
        return shortcut if shortcut else DEFAULT_SHORTCUT

    # === Data providers ===

    @pyqtSlot(result='QVariantList')
    def getAvailableLanguages(self):
        """Get available languages as list of dicts for QML."""
        languages = []
        for code, name in Settings.VALID_LANGUAGES.items():
            languages.append({"code": code, "name": name})
        return languages

    @pyqtSlot(result='QVariantList')
    def getAudioDevices(self):
        """Get audio input devices."""
        # TODO: Integrate with actual audio device enumeration
        # For now, return placeholder
        return [
            {"name": "Default Microphone", "index": -1},
            {"name": "Built-in Microphone", "index": 0}
        ]


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
        """Open KDE System Settings directly to Syllablaze shortcut."""
        from PyQt6.QtCore import QProcess
        logger.info("Opening KDE System Settings (Syllablaze shortcut)")
        # Use kcmshell6 with search parameter to jump directly to Syllablaze
        QProcess.startDetached("kcmshell6", ["kcm_keys", "--args", "Syllablaze"])


class KirigamiSettingsWindow(QWidget):
    """Kirigami-based settings window that replaces PyQt6 SettingsWindow."""

    initialization_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.whisper_model = None
        self.current_model = None

        self.setWindowTitle(f"{APP_NAME} Settings")
        self.setFixedSize(900, 600)

        # Create bridges
        self.settings_bridge = SettingsBridge()
        self.actions_bridge = ActionsBridge()

        # Use QQmlApplicationEngine for reliable QML loading
        self.engine = QQmlApplicationEngine()

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
            logger.info("Kirigami SettingsWindow loaded successfully")
        else:
            logger.error("Failed to load Kirigami SettingsWindow")
            # Print QML errors
            for error in self.engine.rootObjects():
                logger.error(f"QML Error: {error}")

    def show(self):
        """Show the Kirigami settings window."""
        if hasattr(self, "root_window") and self.root_window:
            # Show the QML window directly
            self.root_window.show()

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
