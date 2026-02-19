"""
Recording Dialog Manager for Syllablaze

Manages the recording indicator applet with volume visualization.
Now uses plain QWidget (RecordingApplet) instead of QML for better Wayland/KWin support.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal
from blaze.constants import APPLET_MODE_PERSISTENT

logger = logging.getLogger(__name__)


class _AppletBridge(QObject):
    """Backward-compatible bridge wrapper for RecordingApplet signals.

    Exposes signals in the same format as the old QML RecordingDialogBridge.
    """

    toggleRecordingRequested = pyqtSignal()
    openClipboardRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()
    dismissRequested = pyqtSignal()
    recordingStateChanged = pyqtSignal(bool)
    transcribingStateChanged = pyqtSignal(bool)

    def __init__(self, applet, app_state, parent=None):
        super().__init__(parent)
        self._applet = applet
        self._app_state = app_state

        # Connect applet signals to bridge signals
        applet.toggleRecordingRequested.connect(self.toggleRecordingRequested)
        applet.openClipboardRequested.connect(self.openClipboardRequested)
        applet.openSettingsRequested.connect(self.openSettingsRequested)
        applet.dismissRequested.connect(self.dismissRequested)

        # Connect app state signals
        if app_state:
            app_state.recording_state_changed.connect(self.recordingStateChanged)
            app_state.transcription_state_changed.connect(self.transcribingStateChanged)


class RecordingDialogManager(QObject):
    """Manages the recording indicator applet.

    This is a VIEW component - responds to ApplicationState but doesn't own state.
    Uses RecordingApplet (plain QWidget) for better Wayland/KWin compatibility.
    """

    def __init__(self, settings, app_state, audio_manager=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.app_state = app_state
        self._audio_manager = audio_manager
        self.applet = None
        self.bridge = None  # Backward compatibility

    def set_audio_manager(self, audio_manager):
        """Set audio manager after initialization (called after audio_manager is created)."""
        self._audio_manager = audio_manager
        self._create_applet()

    @property
    def audio_manager(self):
        return self._audio_manager

    def _create_applet(self):
        """Create the RecordingApplet widget (internal)."""
        from blaze.recording_applet import RecordingApplet

        self.applet = RecordingApplet(
            settings=self.settings,
            app_state=self.app_state,
            audio_manager=self._audio_manager,
        )

        # Create backward-compatible bridge
        self.bridge = _AppletBridge(self.applet, self.app_state, self)

        # Connect applet signals to manager handlers
        self.applet.toggleRecordingRequested.connect(self._on_toggle_recording)
        self.applet.openClipboardRequested.connect(self._on_open_clipboard)
        self.applet.openSettingsRequested.connect(self._on_open_settings)
        self.applet.dismissRequested.connect(self._on_dismiss)
        self.applet.windowPositionChanged.connect(self._on_position_changed)
        self.applet.windowSizeChanged.connect(self._on_size_changed)

        # Apply settings
        on_all = self._effective_on_all_desktops()
        if on_all:
            self.applet.set_on_all_desktops(on_all)

        logger.info("RecordingDialogManager: RecordingApplet created")

    def initialize(self):
        """Initialize the recording dialog manager.

        Note: The applet is created later when set_audio_manager() is called,
        after the audio manager is ready.
        """
        logger.info("RecordingDialogManager: Initialized (applet will be created when audio_manager is set)")

    def connect_bridge_signals(self, toggle_recording_callback=None, open_settings_callback=None, dismiss_callback=None):
        """Connect bridge signals to external callbacks.

        Should be called after set_audio_manager() creates the bridge.
        """
        if not self.bridge:
            logger.warning("RecordingDialogManager: Cannot connect bridge signals - bridge not created yet")
            return

        if toggle_recording_callback:
            self.bridge.toggleRecordingRequested.connect(toggle_recording_callback)
        if open_settings_callback:
            self.bridge.openSettingsRequested.connect(open_settings_callback)
        if dismiss_callback:
            self.bridge.dismissRequested.connect(dismiss_callback)

        logger.info("RecordingDialogManager: Bridge signals connected")

    def show(self):
        """Show the applet window.

        Window properties (always-on-top, on-all-desktops) are applied via KWin
        automatically in the applet's showEvent handler.
        """
        if self.applet:
            self.applet.show()
            self.applet.raise_()
            self.applet.requestActivate()

            logger.info("RecordingDialogManager: Applet shown (KWin properties will be applied)")

    def hide(self):
        """Hide the applet window."""
        if self.applet:
            self.applet.hide()
            logger.info("RecordingDialogManager: Applet hidden")

    def is_visible(self):
        """Check if applet should be visible."""
        return self.app_state.is_recording_dialog_visible() if self.app_state else False

    def _effective_on_all_desktops(self):
        """Return on_all_desktops value based on settings.

        Returns True/False only in persistent mode (where it matters).
        Returns False for popup/off modes so the rule is cleared.
        """
        applet_mode = self.settings.get("applet_mode", "popup")
        if applet_mode == APPLET_MODE_PERSISTENT:
            return bool(self.settings.get("applet_onalldesktops", True))
        return False

    def update_always_on_top(self, always_on_top):
        """Update always-on-top setting live."""
        if not self.applet:
            return

        self.applet.update_always_on_top_setting(always_on_top)
        logger.info(f"Always-on-top updated: {always_on_top}")

    def update_on_all_desktops(self, on_all_desktops):
        """Update on-all-desktops setting."""
        if self.settings:
            self.settings.set("applet_onalldesktops", on_all_desktops)

        logger.info(f"On-all-desktops setting changed to: {on_all_desktops}")

        if self.applet and self.applet.isVisible():
            self.applet.set_on_all_desktops(on_all_desktops)

    def update_volume(self, volume):
        """Update volume display - now handled directly by RecordingApplet."""
        pass  # No longer needed - RecordingApplet connects directly to AudioManager

    def update_audio_samples(self, samples):
        """Update audio visualization - now handled directly by RecordingApplet."""
        pass  # No longer needed - RecordingApplet connects directly to AudioManager

    def cleanup(self):
        """Hide the applet and clean up."""
        try:
            if self.applet:
                self.applet.hide()
                self.applet = None
            logger.info("RecordingDialogManager: cleaned up")
        except Exception as e:
            logger.error(f"RecordingDialogManager: cleanup failed: {e}")

    # --- Signal handlers ---

    def _on_toggle_recording(self):
        """Handle toggle recording request from applet."""
        logger.info("RecordingDialogManager: toggleRecording requested")

    def _on_open_clipboard(self):
        """Open clipboard manager."""
        import subprocess
        from PyQt6.QtWidgets import QApplication, QMessageBox

        logger.info("Opening clipboard manager...")

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
            except Exception:
                continue

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

    def _on_open_settings(self):
        """Open settings window."""
        logger.info("RecordingDialogManager: openSettings requested")

    def _on_dismiss(self):
        """Handle applet dismissal."""
        if self.applet and self.applet.is_recording:
            logger.info("Recording active - stopping first")
            self._on_toggle_recording()
        self.hide()

    def _on_position_changed(self, x, y):
        """Save window position when changed."""
        self.settings.set("recording_dialog_position_x", x)
        self.settings.set("recording_dialog_position_y", y)
        logger.info(f"Saved applet position: ({x}, {y})")

    def _on_size_changed(self, size):
        """Save window size when changed."""
        self.settings.set("recording_dialog_size", size)
        logger.info(f"Saved applet size: {size}")
