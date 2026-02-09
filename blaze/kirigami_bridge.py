#!/usr/bin/env python3
"""
Kirigami Bridge for Syllablaze

Provides Python-QML communication bridge for KDE 6 Kirigami integration.
This allows Python backend to communicate with QML/Kirigami frontend.
"""

import os
import sys
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, QTimer
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt6.QtWidgets import QApplication
import logging

logger = logging.getLogger(__name__)


class SettingsBridge(QObject):
    """Bridge for exposing Settings object to QML."""

    # Signals that QML can connect to
    settingChanged = pyqtSignal(str, object)  # key, value

    def __init__(self, settings_obj):
        super().__init__()
        self.settings = settings_obj

    @pyqtSlot(str, result=object)
    def get(self, key):
        """Get a setting value from QML."""
        return self.settings.get(key)

    @pyqtSlot(str, object)
    def set(self, key, value):
        """Set a setting value from QML."""
        try:
            self.settings.set(key, value)
            self.settingChanged.emit(key, value)
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")

    @pyqtSlot(result=list)
    def getAvailableLanguages(self):
        """Get available languages for QML."""
        from blaze.settings import Settings

        return list(Settings.VALID_LANGUAGES.items())


class AudioBridge(QObject):
    """Bridge for exposing AudioManager to QML."""

    # Signals
    audioDevicesChanged = pyqtSignal(list)
    recordingStateChanged = pyqtSignal(bool)

    def __init__(self, audio_manager):
        super().__init__()
        self.audio_manager = audio_manager

    @pyqtSlot(result=list)
    def getAudioDevices(self):
        """Get list of audio devices for QML."""
        # This would integrate with the existing audio device enumeration
        # For now, return a placeholder
        return [{"name": "Default Microphone", "index": 0}]

    @pyqtSlot()
    def startRecording(self):
        """Start recording from QML."""
        if self.audio_manager:
            self.audio_manager.start_recording()
            self.recordingStateChanged.emit(True)

    @pyqtSlot()
    def stopRecording(self):
        """Stop recording from QML."""
        if self.audio_manager:
            self.audio_manager.stop_recording()
            self.recordingStateChanged.emit(False)


class KirigamiBridge:
    """Main bridge class for Kirigami QML integration."""

    def __init__(self):
        self.engine = QQmlApplicationEngine()
        self.bridges = {}

        # Set up QML import paths
        self.setup_qml_paths()

    def setup_qml_paths(self):
        """Set up QML import paths for Kirigami."""
        # Add our QML directory to the import path
        qml_dir = Path(__file__).parent / "qml"
        self.engine.addImportPath(str(qml_dir))

        # Add system Kirigami path
        kirigami_path = "/usr/lib/qt6/qml"
        self.engine.addImportPath(kirigami_path)

    def expose_python_object(self, name, obj):
        """Expose a Python object to QML."""
        self.engine.rootContext().setContextProperty(name, obj)
        logger.info(f"Exposed Python object to QML: {name}")

    def register_qml_type(self, module, version, name, python_class):
        """Register a Python class as a QML type."""
        qmlRegisterType(python_class, module, version, name)
        logger.info(f"Registered QML type: {module}.{version}.{name}")

    def load_qml(self, qml_file):
        """Load and display a QML file."""
        qml_path = Path(__file__).parent / "qml" / qml_file

        if not qml_path.exists():
            logger.error(f"QML file not found: {qml_path}")
            return False

        try:
            self.engine.load(QUrl.fromLocalFile(str(qml_path)))

            if not self.engine.rootObjects():
                logger.error("Failed to load QML file")
                return False

            logger.info(f"QML file loaded successfully: {qml_file}")
            return True

        except Exception as e:
            logger.error(f"Error loading QML file: {e}")
            return False

    def create_settings_bridge(self, settings_obj):
        """Create and expose SettingsBridge."""
        bridge = SettingsBridge(settings_obj)
        self.expose_python_object("settingsBridge", bridge)
        self.bridges["settings"] = bridge
        return bridge

    def create_audio_bridge(self, audio_manager):
        """Create and expose AudioBridge."""
        bridge = AudioBridge(audio_manager)
        self.expose_python_object("audioBridge", bridge)
        self.bridges["audio"] = bridge
        return bridge

    def show(self):
        """Show the QML interface."""
        if not self.engine.rootObjects():
            logger.error("No QML root objects to show")
            return False

        # Get the main window and show it
        root_objects = self.engine.rootObjects()
        if root_objects:
            window = root_objects[0]
            if hasattr(window, "show"):
                window.show()
                logger.info("QML window shown")
                return True

        logger.warning("Could not find showable QML window")
        return False


def test_kirigami_integration():
    """Test Kirigami integration."""
    logger.info("Testing Kirigami integration...")

    # Create application instance
    app = QApplication.instance() or QApplication(sys.argv)

    # Create bridge
    bridge = KirigamiBridge()

    # Test loading a simple QML file
    success = bridge.load_qml("test/TestWindow.qml")

    if success:
        logger.info("Kirigami integration test passed")
        bridge.show()
        return app.exec()
    else:
        logger.error("Kirigami integration test failed")
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(test_kirigami_integration())
