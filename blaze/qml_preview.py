#!/usr/bin/env python3
"""
QML/Kirigami Preview Tool for Syllablaze

This tool allows live preview of QML files during development.
It provides hot-reload functionality and visual testing.
"""

import os
import sys
from pathlib import Path
from PyQt6.QtCore import QUrl, QTimer, pyqtSlot
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication
import logging

logger = logging.getLogger(__name__)


class QMLPreview:
    """Live QML preview with hot-reload functionality."""

    def __init__(self, qml_file_path):
        self.qml_file_path = Path(qml_file_path)
        self.engine = QQmlApplicationEngine()
        self.app = QApplication(sys.argv)

        # Set up file watcher for hot reload
        self.setup_file_watcher()

    def setup_file_watcher(self):
        """Set up file watching for hot reloading."""
        from PyQt6.QtCore import QFileSystemWatcher

        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(str(self.qml_file_path))
        self.watcher.fileChanged.connect(self.on_file_changed)

    @pyqtSlot(str)
    def on_file_changed(self, path):
        """Handle file changes for hot reload."""
        logger.info(f"QML file changed: {path}")
        self.reload_qml()

    def reload_qml(self):
        """Reload the QML file."""
        try:
            # Clear the engine and reload
            self.engine.clearComponentCache()
            self.engine.load(QUrl.fromLocalFile(str(self.qml_file_path)))
            logger.info("QML reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload QML: {e}")

    def preview(self):
        """Start the QML preview."""
        logger.info(f"Starting QML preview: {self.qml_file_path}")

        # Load the QML file
        try:
            self.engine.load(QUrl.fromLocalFile(str(self.qml_file_path)))

            if not self.engine.rootObjects():
                logger.error("Failed to load QML file")
                return False

            logger.info("QML preview started successfully")
            logger.info(
                "Hot reload enabled - file changes will trigger automatic reload"
            )

            # Start the application event loop
            sys.exit(self.app.exec())

        except Exception as e:
            logger.error(f"Error starting QML preview: {e}")
            return False


def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 2:
        print("Usage: python3 qml_preview.py <qml_file>")
        sys.exit(1)

    qml_file = sys.argv[1]

    if not os.path.exists(qml_file):
        print(f"Error: QML file '{qml_file}' not found")
        sys.exit(1)

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    preview = QMLPreview(qml_file)
    sys.exit(preview.preview())


if __name__ == "__main__":
    main()
