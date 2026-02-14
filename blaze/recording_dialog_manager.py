"""
Recording Dialog Manager for Syllablaze

Manages the circular recording indicator dialog with volume visualization.
"""

import os
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot, QUrl
from PyQt6.QtQml import QQmlApplicationEngine
from blaze.settings import Settings

logger = logging.getLogger(__name__)


class AudioBridge(QObject):
    """Bridge exposing recording state and volume to QML."""

    recordingStateChanged = pyqtSignal(bool)  # isRecording
    volumeChanged = pyqtSignal(float)  # 0.0-1.0
    transcribingStateChanged = pyqtSignal(bool)  # isTranscribing
    audioSamplesChanged = pyqtSignal('QVariantList')  # Audio waveform samples

    def __init__(self):
        super().__init__()
        self._is_recording = False
        self._current_volume = 0.0
        self._is_transcribing = False
        self._audio_samples = []

    @pyqtProperty(bool, notify=recordingStateChanged)
    def isRecording(self):
        return self._is_recording

    @pyqtProperty(float, notify=volumeChanged)
    def currentVolume(self):
        return self._current_volume

    @pyqtProperty(bool, notify=transcribingStateChanged)
    def isTranscribing(self):
        return self._is_transcribing

    @pyqtProperty('QVariantList', notify=audioSamplesChanged)
    def audioSamples(self):
        return self._audio_samples

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

    def setAudioSamples(self, samples):
        """Set audio waveform samples (list of floats -1.0 to 1.0)"""
        if isinstance(samples, (list, tuple)) and len(samples) > 0:
            # Keep only last 128 samples for performance
            self._audio_samples = list(samples[-128:])
            self.audioSamplesChanged.emit(self._audio_samples)

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
    windowPositionChanged = pyqtSignal(int, int)  # x, y

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

    @pyqtSlot(int, int)
    def saveWindowPosition(self, x, y):
        """Called from QML when window position changes"""
        logger.info(f"DialogBridge: saveWindowPosition({x}, {y}) called from QML")
        self.windowPositionChanged.emit(x, y)


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
        self.dialog_bridge.windowPositionChanged.connect(self._on_window_position_changed_from_qml)

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

                # Set initial window flags to prevent border flash
                from PyQt6.QtCore import Qt
                settings = Settings()
                always_on_top = settings.get("recording_dialog_always_on_top", True)
                base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
                if always_on_top:
                    initial_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
                else:
                    initial_flags = base_flags
                self.window.setFlags(initial_flags)
                logger.info(f"RecordingDialogManager: Set initial window flags: {initial_flags}")

                # Restore saved window size
                self._restore_window_size()

                # Restore saved window position
                self._restore_window_position()

                # Connect size change handler
                if hasattr(self.window, 'widthChanged'):
                    self.window.widthChanged.connect(self._on_window_size_changed)

                # Position change handlers removed - now handled by QML onXChanged/onYChanged

            else:
                logger.error("RecordingDialogManager: Failed to load QML window")

        except Exception as e:
            logger.error(f"RecordingDialogManager: Initialization failed: {e}", exc_info=True)

    def show(self):
        """Show the recording dialog"""
        if self.window:
            from PyQt6.QtCore import Qt
            settings = Settings()
            always_on_top = settings.get("recording_dialog_always_on_top", True)

            logger.info(f"show() called - setting value: {always_on_top!r} (type: {type(always_on_top).__name__})")

            # Settings.get() already returns a boolean
            always_on_top = bool(always_on_top)

            logger.info(f"show() - always_on_top={always_on_top}")

            # Set Qt window flags
            # Use Qt.Window instead of Qt.Tool for better Wayland control
            # FramelessWindowHint for borderless appearance
            base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
            if always_on_top:
                new_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
                logger.info("Adding WindowStaysOnTopHint flag (using Qt.Window base)")
            else:
                new_flags = base_flags
                logger.info("NOT adding WindowStaysOnTopHint flag (using Qt.Window base)")

            logger.info(f"Setting window flags: {new_flags}")
            self.window.setFlags(new_flags)

            # Show window
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()

            # Restore position after a brief delay (window needs to be fully shown)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self._restore_window_position)

            self._visible = True
            logger.info(f"RecordingDialogManager: Dialog shown (always_on_top={always_on_top})")
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

    def update_always_on_top(self, always_on_top):
        """Update the always-on-top window property"""
        logger.info(f"update_always_on_top() called with: {always_on_top}")

        # If window exists and is visible, hide and show to apply new setting
        if self.window and self._visible:
            logger.info("Window is visible - hiding and reshowing with new setting")
            self.hide()

            # Small delay to ensure settings are persisted before show() reads them
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.show)
        else:
            logger.debug("Window not visible - will apply on next show()")

    def update_recording_state(self, is_recording):
        """Update recording state in QML"""
        self.audio_bridge.setRecording(is_recording)

    def update_volume(self, volume):
        """Update volume level in QML (0.0-1.0)"""
        self.audio_bridge.setVolume(volume)

    def update_audio_samples(self, samples):
        """Update audio waveform samples"""
        self.audio_bridge.setAudioSamples(samples)

    def update_transcribing_state(self, is_transcribing):
        """Update transcription state in QML"""
        self.audio_bridge.setTranscribing(is_transcribing)

    def _restore_window_size(self):
        """Restore saved window size from Settings"""
        if not self.window:
            return

        settings = Settings()
        saved_size = settings.get("recording_dialog_size", 200)

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
            settings = Settings()
            settings.set("recording_dialog_size", int(width))
            logger.info(f"RecordingDialogManager: Saved window size {width}px")

    def _restore_window_position(self):
        """Restore saved window position from Settings"""
        if not self.window:
            logger.warning("Cannot restore position - window is None")
            return

        settings = Settings()
        saved_x = settings.get("recording_dialog_x", None)
        saved_y = settings.get("recording_dialog_y", None)

        # Log current position before restore
        current_x = self.window.property("x")
        current_y = self.window.property("y")
        logger.info(f"Current window position before restore: ({current_x}, {current_y})")

        # Only restore if we have a saved position (both x and y must be set)
        if saved_x is not None and saved_y is not None:
            try:
                logger.info(f"Attempting to restore position to ({saved_x}, {saved_y})")
                self.window.setProperty("x", int(saved_x))
                self.window.setProperty("y", int(saved_y))

                # Verify it was set
                new_x = self.window.property("x")
                new_y = self.window.property("y")
                logger.info(f"Position after setProperty: ({new_x}, {new_y})")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to restore window position: {e}")
        else:
            logger.info(f"No saved position found (x={saved_x}, y={saved_y}), using window manager default")

    def _on_window_position_changed_from_qml(self, x, y):
        """Save window position when changed from QML"""
        if x is not None and y is not None:
            settings = Settings()
            settings.set("recording_dialog_x", int(x))
            settings.set("recording_dialog_y", int(y))
            logger.info(f"RecordingDialogManager: Saved window position from QML ({x}, {y})")

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
