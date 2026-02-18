"""
Recording Dialog Manager for Syllablaze

Manages the recording indicator dialog with volume visualization.
"""

import os
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot, QUrl
from PyQt6.QtQml import QQmlApplicationEngine
from blaze.settings import Settings
from blaze.kwin_rules import (
    save_window_position_to_rule,
    get_saved_position_from_rule,
    is_wayland,
    set_window_on_all_desktops,
    WINDOW_TITLE,
)
from blaze.constants import APPLET_MODE_PERSISTENT
from blaze.svg_renderer_bridge import SvgRendererBridge

logger = logging.getLogger(__name__)


class RecordingDialogBridge(QObject):
    """Bridge between Python backend and QML dialog.

    Provides:
    - State properties (recording status, volume, samples) - READ from ApplicationState
    - User action slots (toggle, dismiss, etc.) - emit signals to Python
    - Window management (size persistence)
    """

    # State change signals (Python -> QML)
    recordingStateChanged = pyqtSignal(bool)
    transcribingStateChanged = pyqtSignal(bool)
    volumeChanged = pyqtSignal(float)
    audioSamplesChanged = pyqtSignal("QVariantList")

    # User action signals (QML -> Python)
    toggleRecordingRequested = pyqtSignal()
    openClipboardRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()
    dismissRequested = pyqtSignal()
    dialogClosedSignal = pyqtSignal()

    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state

        # Audio state (not in ApplicationState)
        self._current_volume = 0.0
        self._audio_samples = []

        # Connect to ApplicationState signals
        if self.app_state:
            self.app_state.recording_state_changed.connect(
                self._on_recording_state_changed
            )
            self.app_state.transcription_state_changed.connect(
                self._on_transcription_state_changed
            )

    # --- Properties (QML reads these) ---

    @pyqtProperty(bool, notify=recordingStateChanged)
    def isRecording(self):
        """Recording status from ApplicationState"""
        return self.app_state.is_recording() if self.app_state else False

    @pyqtProperty(bool, notify=transcribingStateChanged)
    def isTranscribing(self):
        """Transcribing status from ApplicationState"""
        return self.app_state.is_transcribing() if self.app_state else False

    @pyqtProperty(float, notify=volumeChanged)
    def currentVolume(self):
        """Current audio volume level (0.0-1.0)"""
        return self._current_volume

    @pyqtProperty("QVariantList", notify=audioSamplesChanged)
    def audioSamples(self):
        """Audio waveform samples for visualization"""
        return self._audio_samples

    # --- Slots (QML calls these) ---

    @pyqtSlot()
    def toggleRecording(self):
        """User clicked to toggle recording"""
        logger.info("RecordingDialogBridge: toggleRecording() called from QML")
        self.toggleRecordingRequested.emit()

    @pyqtSlot()
    def openClipboard(self):
        """User wants to open clipboard manager"""
        logger.info("RecordingDialogBridge: openClipboard() called from QML")
        self.openClipboardRequested.emit()

    @pyqtSlot()
    def openSettings(self):
        """User wants to open settings window"""
        logger.info("RecordingDialogBridge: openSettings() called from QML")
        self.openSettingsRequested.emit()

    @pyqtSlot()
    def dismissDialog(self):
        """User dismissed the dialog"""
        logger.info("RecordingDialogBridge: dismissDialog() called from QML")
        self.dismissRequested.emit()

    @pyqtSlot()
    def dialogClosed(self):
        """Dialog window was closed"""
        logger.info("RecordingDialogBridge: dialogClosed() called from QML")
        self.dialogClosedSignal.emit()

    @pyqtSlot(int)
    def saveWindowSize(self, size):
        """Save window size when user resizes with scroll wheel"""
        logger.info(f"RecordingDialogBridge: saveWindowSize({size}) called from QML")
        settings = Settings()
        settings.set("recording_dialog_size", size)
        # Also update KWin rule
        from blaze.kwin_rules import save_window_position_to_rule

        save_window_position_to_rule(0, 0, size, size)

    @pyqtSlot()
    def getWindowSize(self):
        """Get saved window size"""
        settings = Settings()
        return settings.get("recording_dialog_size", 200)

    # --- Methods (Python calls these) ---

    def _on_recording_state_changed(self, is_recording):
        """Relay recording state change from ApplicationState to QML"""
        logger.info(f"RecordingDialogBridge: Recording state changed to {is_recording}")
        self.recordingStateChanged.emit(is_recording)

    def _on_transcription_state_changed(self, is_transcribing):
        """Relay transcription state change from ApplicationState to QML"""
        logger.info(
            f"RecordingDialogBridge: Transcribing state changed to {is_transcribing}"
        )
        self.transcribingStateChanged.emit(is_transcribing)

    def setVolume(self, volume):
        """Update volume level (called by AudioManager)"""
        volume = max(0.0, min(1.0, volume))
        self._current_volume = volume
        self.volumeChanged.emit(volume)

    def setAudioSamples(self, samples):
        """Update audio samples (called by AudioManager)"""
        if isinstance(samples, (list, tuple)) and len(samples) > 0:
            # Keep only last 128 samples for performance
            self._audio_samples = list(samples[-128:])
            self.audioSamplesChanged.emit(self._audio_samples)


class RecordingDialogManager(QObject):
    """Manages the recording indicator dialog.

    This is a VIEW component - responds to ApplicationState but doesn't own state.
    """

    def __init__(self, settings, app_state, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.app_state = app_state
        self.engine = None
        self.window = None
        self.bridge = RecordingDialogBridge(app_state)
        self.svg_bridge = None  # Will be initialized in initialize()

        # Connect bridge signals
        self.bridge.dismissRequested.connect(self._on_dismiss)
        self.bridge.openClipboardRequested.connect(self._on_open_clipboard)

    def initialize(self):
        """Create QML engine and load dialog"""
        try:
            logger.info("RecordingDialogManager: Initializing...")

            self.engine = QQmlApplicationEngine()
            self.engine.addImportPath("/usr/lib/qt6/qml")

            # Register bridges
            context = self.engine.rootContext()
            context.setContextProperty("dialogBridge", self.bridge)

            # Create and register SVG renderer bridge
            self.svg_bridge = SvgRendererBridge()
            context.setContextProperty("svgBridge", self.svg_bridge)
            logger.info("RecordingDialogManager: SVG bridge registered")

            # Load QML - use the new visualizer
            qml_path = os.path.join(
                os.path.dirname(__file__), "qml", "RecordingDialogVisualizer.qml"
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

                # Set window flags
                from PyQt6.QtCore import Qt

                always_on_top = self.settings.get(
                    "recording_dialog_always_on_top", True
                )
                base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
                if always_on_top:
                    initial_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
                else:
                    initial_flags = base_flags
                self.window.setFlags(initial_flags)

                # Restore size
                self._restore_window_size()

                # Connect size handler
                if hasattr(self.window, "widthChanged"):
                    self.window.widthChanged.connect(self._on_window_size_changed)

                # Initialize KWin rule
                from blaze.kwin_rules import create_or_update_kwin_rule

                create_or_update_kwin_rule(
                    enable_keep_above=always_on_top,
                    on_all_desktops=self._effective_on_all_desktops(),
                )

                # In persistent mode the QML window auto-shows via `visible: true`
                # before Python's show() is ever called, so set_window_on_all_desktops()
                # never runs.  Connect to visibilityChanged and fire once on the first
                # non-Hidden event — this is deterministic (compositor has acknowledged
                # the surface) unlike an arbitrary QTimer delay.
                on_all = self._effective_on_all_desktops()
                if on_all:
                    from PyQt6.QtGui import QWindow as _QWindow

                    def _apply_on_all_desktops(visibility):
                        if visibility != _QWindow.Visibility.Hidden:
                            self.window.visibilityChanged.disconnect(_apply_on_all_desktops)
                            set_window_on_all_desktops(WINDOW_TITLE, True)

                    self.window.visibilityChanged.connect(_apply_on_all_desktops)
            else:
                logger.error("RecordingDialogManager: Failed to load QML window")

        except Exception as e:
            logger.error(
                f"RecordingDialogManager: Initialization failed: {e}", exc_info=True
            )

    def show(self):
        """Show the dialog window"""
        if self.window:
            from PyQt6.QtCore import Qt

            always_on_top = bool(self.settings.get("recording_dialog_always_on_top"))

            # Sync KWin rule
            from blaze.kwin_rules import create_or_update_kwin_rule

            create_or_update_kwin_rule(
                enable_keep_above=always_on_top,
                on_all_desktops=self._effective_on_all_desktops(),
            )

            # Set flags
            base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
            if always_on_top:
                new_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
            else:
                new_flags = base_flags
            self.window.setFlags(new_flags)

            # Show window
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()

            # Apply on-all-desktops live (KWin rules only fire at window creation)
            on_all = self._effective_on_all_desktops()
            set_window_on_all_desktops(WINDOW_TITLE, on_all)

            logger.info(
                f"RecordingDialogManager: Dialog shown (always_on_top={always_on_top}, on_all_desktops={on_all})"
            )

    def hide(self):
        """Hide the dialog window"""
        if self.window:
            self.window.hide()
            logger.info("RecordingDialogManager: Dialog hidden")

    def is_visible(self):
        """Check if dialog should be visible"""
        return self.app_state.is_recording_dialog_visible() if self.app_state else False

    def _effective_on_all_desktops(self):
        """Return on_all_desktops value to pass to KWin rule.

        Returns True/False only in persistent mode (where it matters).
        Returns False for popup/off modes so the rule is cleared.
        """
        applet_mode = self.settings.get("applet_mode", "popup")
        if applet_mode == APPLET_MODE_PERSISTENT:
            return bool(self.settings.get("applet_onalldesktops", True))
        return False

    def update_always_on_top(self, always_on_top):
        """Update always-on-top setting live"""
        if not self.window:
            return

        if self.window.isVisible():
            self.hide()
            self.show()
        logger.info(f"Always-on-top updated: {always_on_top}")

    def update_on_all_desktops(self, on_all_desktops):
        """Update on-all-desktops KWin rule and apply live to current window"""
        always_on_top = bool(self.settings.get("recording_dialog_always_on_top", True))
        from blaze.kwin_rules import create_or_update_kwin_rule
        create_or_update_kwin_rule(enable_keep_above=always_on_top, on_all_desktops=on_all_desktops)
        # Also apply immediately to the running window via KWin scripting
        set_window_on_all_desktops(WINDOW_TITLE, on_all_desktops)
        logger.info(f"On-all-desktops updated: {on_all_desktops}")

    def update_volume(self, volume):
        """Update volume display"""
        self.bridge.setVolume(volume)

    def update_audio_samples(self, samples):
        """Update audio visualization"""
        self.bridge.setAudioSamples(samples)

    def _restore_window_size(self):
        """Restore saved window size"""
        if not self.window:
            return

        saved_size = None

        # Try KWin rules first
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
                parts = result.stdout.strip().split(",")
                if len(parts) == 2:
                    saved_size = int(parts[0])
        except Exception as e:
            logger.debug(f"Could not read size from KWin: {e}")

        # Fallback to settings
        if saved_size is None:
            saved_size = self.settings.get("recording_dialog_size", 200)

        # Apply size
        try:
            saved_size = max(100, min(500, int(saved_size)))
            self.window.setProperty("width", saved_size)
            self.window.setProperty("height", saved_size)
            logger.info(f"Restored window size: {saved_size}px")
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to restore size: {e}")

    def _on_window_size_changed(self):
        """Save size when changed"""
        if not self.window:
            return

        width = self.window.property("width")
        if width:
            self.settings.set("recording_dialog_size", int(width))
            logger.info(f"Saved window size: {width}px")

    def cleanup(self):
        """Hide the dialog and destroy the QML engine"""
        try:
            if self.window:
                self.window.hide()
                self.window = None
            if self.engine:
                self.engine.deleteLater()
                self.engine = None
            logger.info("RecordingDialogManager: cleaned up")
        except Exception as e:
            logger.error(f"RecordingDialogManager: cleanup failed: {e}")

    def _on_dismiss(self):
        """Handle dialog dismissal"""
        if self.bridge.isRecording:
            logger.info("Recording active - stopping first")
            self.bridge.toggleRecordingRequested.emit()
        self.hide()

    def _on_open_clipboard(self):
        """Open clipboard manager"""
        import subprocess
        from PyQt6.QtWidgets import QApplication, QMessageBox

        logger.info("Opening clipboard manager...")

        # Try multiple methods
        methods = [
            [
                "qdbus",
                "org.kde.klipper",
                "/klipper",
                "org.kde.klipper.klipper.showKlipperManuallyInvokeActionMenu",
            ],
        ]

        for cmd in methods:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                if result.returncode == 0:
                    logger.info("Opened clipboard via qdbus")
                    return
            except:
                continue

        # Fallback: show clipboard content
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                msg = QMessageBox()
                msg.setWindowTitle("Clipboard")
                msg.setText(text[:200] + ("..." if len(text) > 200 else ""))
                msg.exec()
        except Exception as e:
            logger.error(f"Failed to access clipboard: {e}")
