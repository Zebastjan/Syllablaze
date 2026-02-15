"""
Recording Dialog Manager for Syllablaze

Manages the circular recording indicator dialog with volume visualization.
"""

import os
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot, QUrl
from PyQt6.QtQml import QQmlApplicationEngine
from blaze.settings import Settings
from blaze.kwin_rules import is_wayland

logger = logging.getLogger(__name__)


class AudioBridge(QObject):
    """Bridge exposing recording state and volume to QML."""

    recordingStateChanged = pyqtSignal(bool)  # isRecording
    volumeChanged = pyqtSignal(float)  # 0.0-1.0
    transcribingStateChanged = pyqtSignal(bool)  # isTranscribing
    audioSamplesChanged = pyqtSignal("QVariantList")  # Audio waveform samples

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

    @pyqtProperty("QVariantList", notify=audioSamplesChanged)
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

    @pyqtSlot()
    def isWayland(self):
        """Check if running on Wayland"""
        return is_wayland()


class RecordingDialogManager(QObject):
    """Manages the circular recording indicator dialog.

    This is a VIEW component - it responds to ApplicationState changes
    but does not own visibility state.
    """

    def __init__(self, settings, app_state, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.app_state = app_state
        self.engine = None
        self.window = None
        self.audio_bridge = AudioBridge()
        self.dialog_bridge = DialogBridge()
        self._kde_window_manager = None

        # Connect dialog bridge signals for internal handling
        self.dialog_bridge.dismissRequested.connect(self._on_dismiss)
        self.dialog_bridge.openClipboardRequested.connect(self._on_open_clipboard)
        self.dialog_bridge.windowPositionChanged.connect(
            self._on_window_position_changed_from_qml
        )

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
                os.path.dirname(__file__), "qml", "RecordingDialog.qml"
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

                settings = self.settings
                always_on_top = settings.get("recording_dialog_always_on_top", True)
                base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
                if always_on_top:
                    initial_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
                else:
                    initial_flags = base_flags
                self.window.setFlags(initial_flags)
                logger.info(
                    f"RecordingDialogManager: Set initial window flags: {initial_flags}"
                )

                # Restore saved window size
                self._restore_window_size()

                # Connect size change handler
                if hasattr(self.window, "widthChanged"):
                    self.window.widthChanged.connect(self._on_window_size_changed)

                # PHASE 2: Sync initial KWin rule with current setting (critical for Wayland)
                # This ensures the KWin rule matches the user's setting from startup,
                # not just when they toggle it in the UI.
                #
                # ARCHITECTURAL NOTE: This can be refactored to use WindowSettingsManager:
                #   from blaze.managers.window_settings_manager import WindowSettingsManager
                #   manager = WindowSettingsManager()
                #   success, error = manager.initialize_kwin_rule(
                #       "Recording Dialog",
                #       "recording_dialog_always_on_top"
                #   )
                settings = self.settings
                initial_always_on_top = settings.get('recording_dialog_always_on_top')
                logger.info(f"Initializing KWin rule with always_on_top={initial_always_on_top}")

                from blaze.kwin_rules import create_or_update_kwin_rule
                success = create_or_update_kwin_rule(enable_keep_above=initial_always_on_top)
                if not success:
                    logger.warning("Failed to initialize KWin rule - always-on-top may not work correctly")
                else:
                    logger.info("KWin rule initialized successfully")

            else:
                logger.error("RecordingDialogManager: Failed to load QML window")

        except Exception as e:
            logger.error(
                f"RecordingDialogManager: Initialization failed: {e}", exc_info=True
            )

    def show(self):
        """Show the recording dialog window (Qt operation only)."""
        if self.window:
            from PyQt6.QtCore import Qt

            # Get always-on-top setting
            always_on_top = self.settings.get("recording_dialog_always_on_top")

            logger.info(
                f"show() called - setting value: {always_on_top!r} (type: {type(always_on_top).__name__})"
            )

            # Settings.get() already returns a boolean
            always_on_top = bool(always_on_top)

            logger.info(f"show() - always_on_top={always_on_top}")

            # Sync KWin rule with current setting (ensures KWin behavior matches Qt flags)
            from blaze.kwin_rules import create_or_update_kwin_rule
            create_or_update_kwin_rule(enable_keep_above=always_on_top)
            logger.info(f"Synced KWin rule: above={always_on_top}")

            # PHASE 5: Set Qt window flags
            # WAYLAND/KWIN: KWin rules are what actually control window behavior.
            # Qt window flags are set as well (some compositors may respect them),
            # but KWin rules in ~/.config/kwinrulesrc are the real control mechanism.
            # Use Qt.Window instead of Qt.Tool for better Wayland control
            # FramelessWindowHint for borderless appearance
            base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
            if always_on_top:
                new_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
                logger.info("Adding WindowStaysOnTopHint flag (using Qt.Window base)")
            else:
                new_flags = base_flags
                logger.info(
                    "NOT adding WindowStaysOnTopHint flag (using Qt.Window base)"
                )

            logger.info(f"Setting window flags: {new_flags}")
            self.window.setFlags(new_flags)

            # Show window
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()

            logger.info(
                f"RecordingDialogManager: Dialog window shown (always_on_top={always_on_top})"
            )
        else:
            logger.warning(
                "RecordingDialogManager: Cannot show - window not initialized"
            )

    def hide(self):
        """Hide the recording dialog window (Qt operation only)."""
        if self.window:
            self.window.hide()
            logger.info("RecordingDialogManager: Dialog window hidden")

    def is_visible(self):
        """Check if the dialog should be visible (queries ApplicationState)."""
        return self.app_state.is_recording_dialog_visible() if self.app_state else False

    def update_always_on_top(self, always_on_top):
        """Update the always-on-top window property live (no restart needed)."""
        logger.info(f"update_always_on_top() called with: {always_on_top}")

        if not self.window:
            logger.warning("Cannot update always-on-top - window not initialized")
            return

        # If window is visible, refresh it to apply new setting
        if self._visible:
            logger.info("Window visible - refreshing to apply new always-on-top setting")
            self.hide()
            self.show()  # Direct synchronous call - mimics manual restart pattern
        else:
            logger.debug("Window not visible - will apply on next show()")

        logger.info(f"Always-on-top update complete: {always_on_top}")

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
        """Restore saved window size from KWin rules (or Settings as fallback)"""
        if not self.window:
            return

        saved_size = None

        # Try to get size from KWin rules first
        try:
            from blaze.kwin_rules import find_or_create_rule_group, KWINRULESRC
            import subprocess

            group = find_or_create_rule_group()
            result = subprocess.run(
                [
                    "kreadconfig6",
                    "--file",
                    KWINRULESRC,
                    "--group",
                    group,
                    "--key",
                    "size",
                ],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0 and result.stdout.strip():
                size_str = result.stdout.strip()
                parts = size_str.split(",")
                if len(parts) == 2:
                    saved_size = int(parts[0])  # Use width
                    logger.info(f"Found size in KWin rules: {saved_size}px")
        except Exception as e:
            logger.debug(f"Could not read size from KWin rules: {e}")

        # Fall back to Settings
        if saved_size is None:
            settings = Settings()
            saved_size = settings.get("recording_dialog_size", 200)
            logger.info(f"Using size from Settings: {saved_size}px")

        try:
            saved_size = int(saved_size)
            # Clamp to reasonable range
            saved_size = max(100, min(500, saved_size))

            self.window.setProperty("width", saved_size)
            self.window.setProperty("height", saved_size)
            logger.info(
                f"RecordingDialogManager: Restored window size to {saved_size}px"
            )
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
        """Position restore - no-op (position saving disabled due to KDE/Wayland limitations)"""
        # Position saving has been disabled - KDE/Wayland doesn't reliably support it
        pass

    def _on_window_position_changed_from_qml(self, x, y):
        """Position change handler - no-op (position saving disabled due to KDE/Wayland limitations)"""
        # Position saving has been disabled - KDE/Wayland doesn't reliably support it
        pass

    def _on_dismiss(self):
        """Hide the dialog when dismissed. Stop recording if active."""
        # If recording is active, stop it before dismissing
        if self.audio_bridge.isRecording:
            logger.info("Recording active during dismiss - stopping recording first")
            self.dialog_bridge.toggleRecordingRequested.emit()

        self.hide()

    def _on_open_clipboard(self):
        """Open KDE clipboard manager via D-Bus or show clipboard content"""
        import subprocess
        from PyQt6.QtWidgets import QApplication

        logger.info("Attempting to open clipboard manager...")

        try:
            # Method 1: Try Klipper via qdbus (KDE)
            result = subprocess.run(
                [
                    "qdbus",
                    "org.kde.klipper",
                    "/klipper",
                    "org.kde.klipper.klipper.showKlipperManuallyInvokeActionMenu",
                ],
                capture_output=True,
                timeout=2,
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
            subprocess.Popen(
                [
                    "qdbus",
                    "org.kde.plasmashell",
                    "/PlasmaShell",
                    "org.kde.PlasmaShell.evaluateScript",
                    "const clipboardApplet = desktops().map(d => d.widgets('org.kde.plasma.clipboard')).flat()[0]; if (clipboardApplet) clipboardApplet.showPopup();",
                ]
            )
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
                msg.setText(
                    f"Current clipboard:\n\n{text[:200]}{'...' if len(text) > 200 else ''}"
                )
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            else:
                logger.info("Clipboard is empty")
        except Exception as e:
            logger.error(f"Failed to access clipboard: {e}")
