"""
Kirigami Integration Layer for Syllablaze

This module replaces PyQt6 SettingsWindow with Kirigami QML interface.
"""

import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, Qt
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QGuiApplication

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


class SettingsBridge(QObject):
    """Bridge between Python settings and QML interface."""

    def __init__(self):
        super().__init__()
        self.settings = Settings()

    @pyqtSlot(str)
    def get(self, key):
        """Get a setting value from Python."""
        return str(self.settings.get(key, ""))

    @pyqtSlot(str, str)
    def set(self, key, value):
        """Set a setting value from QML."""
        self.settings.set(key, value)

    @pyqtSlot()
    def getAvailableLanguages(self):
        """Get available languages for QML."""
        from blaze.settings import Settings

        languages = []
        for code, name in Settings.VALID_LANGUAGES.items():
            languages.append({"key": code, "value": name})
        return languages


class KirigamiSettingsWindow(QWidget):
    """Kirigami-based settings window that replaces PyQt6 SettingsWindow."""

    initialization_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings_bridge = SettingsBridge()
        self.settings = Settings()
        self.whisper_model = None
        self.current_model = None

        self.setWindowTitle(f"{APP_NAME} Settings")
        self.setFixedSize(600, 500)

        # Use QQmlApplicationEngine for reliable QML loading
        self.engine = QQmlApplicationEngine()

        # Register settings bridge
        root_context = self.engine.rootContext()
        if root_context:
            root_context.setContextProperty("settingsBridge", self.settings_bridge)

        # Load Kirigami settings window
        qml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "qml/SyllablazeSettings.qml"
        )
        print(f"Loading QML from: {qml_path}")
        self.engine.load(QUrl.fromLocalFile(qml_path))

        # Store the root object
        root_objects = self.engine.rootObjects()
        if root_objects:
            self.root_window = root_objects[0]
            print("Kirigami SettingsWindow loaded successfully")
        else:
            print("Failed to load Kirigami SettingsWindow")

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
            print("Cannot show: No QML window loaded")

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
        # activateWindow method is not available on QWindow, use requestActivate instead
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
            print(f"Failed to set model: {e}")


def show_kirigami_settings():
    """Display Kirigami settings window (for testing)."""
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = KirigamiSettingsWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    # Test Kirigami settings window
    show_kirigami_settings()
