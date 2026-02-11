"""
Recording Dialog Manager for Syllablaze

Manages the circular recording indicator dialog with volume visualization.
"""

import os
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot, QUrl, QSettings
from PyQt6.QtQml import QQmlApplicationEngine

logger = logging.getLogger(__name__)


class AudioBridge(QObject):
    """Bridge exposing recording state and volume to QML."""

    recordingStateChanged = pyqtSignal(bool)  # isRecording
    volumeChanged = pyqtSignal(float)  # 0.0-1.0
    transcribingStateChanged = pyqtSignal(bool)  # isTranscribing

    def __init__(self):
        super().__init__()
        self._is_recording = False
        self._current_volume = 0.0
        self._is_transcribing = False

    @pyqtProperty(bool, notify=recordingStateChanged)
    def isRecording(self):
        return self._is_recording

    @pyqtProperty(float, notify=volumeChanged)
    def currentVolume(self):
        return self._current_volume

    @pyqtProperty(bool, notify=transcribingStateChanged)
    def isTranscribing(self):
        return self._is_transcribing

    def setRecording(self, recording):
        if self._is_recording != recording:
            self._is_recording = recording
            self.recordingStateChanged.emit(recording)
            logger.info(f"AudioBridge: Recording state changed to {recording}")

    def setVolume(self, volume):
        # Clamp volume to 0.0-1.0 range
        volume = max(0.0, min(1.0, volume))
        self._current_volume = volume
        self.volumeChanged.emit(volume)

    def setTranscribing(self, transcribing):
        if self._is_transcribing != transcribing:
            self._is_transcribing = transcribing
            self.transcribingStateChanged.emit(transcribing)
            logger.info(f"AudioBridge: Transcribing state changed to {transcribing}")


class DialogBridge(QObject):
    """Bridge for dialog actions triggered from QML."""

    toggleRecordingRequested = pyqtSignal()
    openClipboardRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()
    dismissRequested = pyqtSignal()
    dialogClosedSignal = pyqtSignal()

    @pyqtSlot()
    def toggleRecording(self):
        logger.info("DialogBridge: toggleRecording() called from QML")
        self.toggleRecordingRequested.emit()

    @pyqtSlot()
    def openClipboard(self):
        logger.info("DialogBridge: openClipboard() called from QML")
        self.openClipboardRequested.emit()

    @pyqtSlot()
    def openSettings(self):
        logger.info("DialogBridge: openSettings() called from QML")
        self.openSettingsRequested.emit()

    @pyqtSlot()
    def dismissDialog(self):
        logger.info("DialogBridge: dismissDialog() called from QML")
        self.dismissRequested.emit()

    @pyqtSlot()
    def dialogClosed(self):
        logger.info("DialogBridge: dialogClosed() called from QML")
        self.dialogClosedSignal.emit()


class RecordingDialogManager(QObject):
    """Manages the circular recording indicator dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = None
        self.window = None
        self.audio_bridge = AudioBridge()
        self.dialog_bridge = DialogBridge()
        self._visible = False

        # Connect dialog bridge signals for internal handling
        self.dialog_bridge.dismissRequested.connect(self._on_dismiss)
        self.dialog_bridge.openClipboardRequested.connect(self._on_open_clipboard)

    def initialize(self):
        """Create QML engine and load RecordingDialog.qml"""
        try:
            logger.info("RecordingDialogManager: Initializing...")

            self.engine = QQmlApplicationEngine()

            # Add Qt6 QML import path
            self.engine.addImportPath("/usr/lib/qt6/qml")
            logger.info(f"QML Import Paths: {self.engine.importPathList()}")

            # Register bridges as context properties
            context = self.engine.rootContext()
            context.setContextProperty("audioBridge", self.audio_bridge)
            context.setContextProperty("dialogBridge", self.dialog_bridge)

            # Load QML file
            qml_path = os.path.join(
                os.path.dirname(__file__),
                "qml",
                "RecordingDialog.qml"
            )
            logger.info(f"RecordingDialogManager: Loading QML from {qml_path}")

            if not os.path.exists(qml_path):
                logger.error(f"QML file not found: {qml_path}")
                return

            self.engine.load(QUrl.fromLocalFile(qml_path))

            # Get window reference
            root_objects = self.engine.rootObjects()
            if root_objects:
                self.window = root_objects[0]
                logger.info("RecordingDialogManager: QML window loaded successfully")

                # Restore saved window size
                self._restore_window_size()

                # Connect size change handler
                if hasattr(self.window, 'widthChanged'):
                    self.window.widthChanged.connect(self._on_window_size_changed)
            else:
                logger.error("RecordingDialogManager: Failed to load QML window")
                # Print QML errors if any
                if self.engine:
                    for error in self.engine.errors():
                        logger.error(f"QML Error: {error.toString()}")

        except Exception as e:
            logger.error(f"RecordingDialogManager: Initialization failed: {e}", exc_info=True)

    def show(self):
        """Show the recording dialog"""
        if self.window:
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()
            self._visible = True
            logger.info("RecordingDialogManager: Dialog shown")
        else:
            logger.warning("RecordingDialogManager: Cannot show - window not initialized")

    def hide(self):
        """Hide the recording dialog"""
        if self.window:
            self.window.hide()
            self._visible = False
            logger.info("RecordingDialogManager: Dialog hidden")

    def is_visible(self):
        """Check if the dialog is currently visible"""
        return self._visible

    def update_recording_state(self, is_recording):
        """Update recording state in QML"""
        self.audio_bridge.setRecording(is_recording)

    def update_volume(self, volume):
        """Update volume level in QML (0.0-1.0)"""
        self.audio_bridge.setVolume(volume)

    def update_transcribing_state(self, is_transcribing):
        """Update transcription state in QML"""
        self.audio_bridge.setTranscribing(is_transcribing)

    def _restore_window_size(self):
        """Restore saved window size from QSettings"""
        if not self.window:
            return

        settings = QSettings("Syllablaze", "RecordingDialog")
        saved_size = settings.value("window_size", 200)

        try:
            saved_size = int(saved_size)
            # Clamp to reasonable range
            saved_size = max(100, min(500, saved_size))

            self.window.setProperty("width", saved_size)
            self.window.setProperty("height", saved_size)
            logger.info(f"RecordingDialogManager: Restored window size to {saved_size}px")
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to restore window size: {e}")

    def _on_window_size_changed(self):
        """Save window size when it changes"""
        if not self.window:
            return

        width = self.window.property("width")
        if width:
            settings = QSettings("Syllablaze", "RecordingDialog")
            settings.setValue("window_size", int(width))
            logger.debug(f"RecordingDialogManager: Saved window size {width}px")

    def _on_dismiss(self):
        """Hide the dialog when dismissed"""
        self.hide()

    def _on_open_clipboard(self):
        """Open KDE clipboard manager via D-Bus or show clipboard content"""
        import subprocess
        from PyQt6.QtWidgets import QApplication

        logger.info("Attempting to open clipboard manager...")

        try:
            # Method 1: Try Klipper via qdbus (KDE)
            result = subprocess.run(
                ["qdbus", "org.kde.klipper", "/klipper",
                 "org.kde.klipper.klipper.showKlipperManuallyInvokeActionMenu"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                logger.info("Opened Klipper clipboard manager via qdbus")
                return
            else:
                logger.warning(f"Klipper qdbus failed: {result.stderr.decode()}")
        except FileNotFoundError:
            logger.warning("qdbus command not found")
        except subprocess.TimeoutExpired:
            logger.warning("Klipper qdbus timeout")
        except Exception as e:
            logger.warning(f"Klipper qdbus error: {e}")

        try:
            # Method 2: Try klipper directly
            subprocess.Popen(["klipper"])
            logger.info("Launched Klipper directly")
            return
        except FileNotFoundError:
            logger.warning("Klipper executable not found")
        except Exception as e:
            logger.warning(f"Failed to launch Klipper: {e}")

        try:
            # Method 3: Try plasma clipboard applet
            subprocess.Popen(["qdbus", "org.kde.plasmashell", "/PlasmaShell",
                            "org.kde.PlasmaShell.evaluateScript",
                            "const clipboardApplet = desktops().map(d => d.widgets('org.kde.plasma.clipboard')).flat()[0]; if (clipboardApplet) clipboardApplet.showPopup();"])
            logger.info("Triggered Plasma clipboard applet")
            return
        except Exception as e:
            logger.warning(f"Failed to trigger Plasma clipboard: {e}")

        # Method 4: Fallback - show current clipboard content as notification
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                logger.info(f"Clipboard content: {text[:100]}...")
                # Show notification with clipboard content
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setWindowTitle("Clipboard Content")
                msg.setText(f"Current clipboard:\n\n{text[:200]}{'...' if len(text) > 200 else ''}")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            else:
                logger.info("Clipboard is empty")
        except Exception as e:
            logger.error(f"Failed to access clipboard: {e}")
