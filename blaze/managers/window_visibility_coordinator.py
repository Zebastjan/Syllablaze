from PyQt6.QtCore import QObject, QTimer
from blaze.constants import APPLET_MODE_OFF, APPLET_MODE_POPUP
import logging

logger = logging.getLogger(__name__)

# Delay (ms) before hiding dialog after transcription finishes in popup mode
POPUP_HIDE_DELAY_MS = 500


class WindowVisibilityCoordinator(QObject):
    """Coordinates window visibility across app state, UI, and tray menu.

    Supports three applet modes via the 'applet_mode' setting:
      - 'off'        — dialog is never shown automatically
      - 'persistent' — dialog is always visible (default legacy behaviour)
      - 'popup'      — dialog auto-shows on record start, auto-hides after
                       transcription completes
    """

    def __init__(self, recording_dialog, app_state, tray_menu_manager, settings_bridge,
                 settings=None):
        """Initialize window visibility coordinator

        Args:
            recording_dialog: RecordingDialogManager instance
            app_state: ApplicationState instance
            tray_menu_manager: TrayMenuManager instance
            settings_bridge: SettingsBridge from settings window
            settings: Settings instance (needed for applet_mode lookup)
        """
        super().__init__()
        self.recording_dialog = recording_dialog
        self.app_state = app_state
        self.tray_menu_manager = tray_menu_manager
        self.settings_bridge = settings_bridge
        self.settings = settings

        # Timer used to delay hiding in popup mode
        self._popup_hide_timer = QTimer(self)
        self._popup_hide_timer.setSingleShot(True)
        self._popup_hide_timer.setInterval(POPUP_HIDE_DELAY_MS)
        self._popup_hide_timer.timeout.connect(self._popup_hide_now)

    # ------------------------------------------------------------------
    # Popup mode helpers
    # ------------------------------------------------------------------

    def _applet_mode(self):
        """Return the current applet_mode string, defaulting to 'popup'."""
        if self.settings:
            return self.settings.get("applet_mode", APPLET_MODE_POPUP)
        return APPLET_MODE_POPUP

    def connect_to_app_state(self, app_state=None):
        """Connect popup auto-show/hide to ApplicationState signals.

        Call this after the coordinator is fully wired up (i.e. after
        _connect_signals in main.py).  Pass app_state to override the
        instance stored at construction time.
        """
        state = app_state or self.app_state
        if state:
            state.recording_started.connect(self._on_recording_started)
            state.transcription_stopped.connect(self._on_transcription_complete)
            logger.info("WindowVisibilityCoordinator: connected to app_state for popup mode")

    def _on_recording_started(self):
        """Auto-show dialog when recording starts (popup mode only)."""
        if self._applet_mode() == APPLET_MODE_POPUP:
            logger.info("Popup mode: showing dialog on recording start")
            # Cancel any pending hide
            self._popup_hide_timer.stop()
            if self.app_state:
                self.app_state.set_recording_dialog_visible(True, source="popup_start")

    def _on_transcription_complete(self):
        """Auto-hide dialog after transcription completes (popup mode only)."""
        if self._applet_mode() == APPLET_MODE_POPUP:
            logger.info(f"Popup mode: scheduling dialog hide in {POPUP_HIDE_DELAY_MS}ms")
            self._popup_hide_timer.start()

    def _popup_hide_now(self):
        """Actually hide the dialog (called by timer)."""
        logger.info("Popup mode: hiding dialog after transcription")
        if self.app_state:
            self.app_state.set_recording_dialog_visible(False, source="popup_complete")

    # ------------------------------------------------------------------
    # Core visibility API
    # ------------------------------------------------------------------

    def toggle_visibility(self, source="unknown"):
        """Toggle recording dialog visibility

        Args:
            source (str): Source of the toggle request for debugging
        """
        if not self.recording_dialog or not self.app_state:
            logger.warning(f"Cannot toggle dialog visibility: components not initialized (source: {source})")
            return

        current_visible = self.app_state.is_recording_dialog_visible()
        self.app_state.set_recording_dialog_visible(not current_visible, source)

    def on_dialog_visibility_changed(self, visible, source):
        """Handle recording dialog visibility changes from ApplicationState

        This is the single handler for ALL visibility changes.
        ApplicationState is the source of truth.

        In 'off' mode, show requests from non-popup sources are blocked.

        Args:
            visible (bool): True to show dialog, False to hide
            source (str): Source of the change (startup, settings_ui, tray_menu, dismissal)
        """
        if not self.recording_dialog:
            logger.warning(f"Cannot update dialog visibility: dialog not initialized (source: {source})")
            return

        # In 'off' mode, block all show attempts
        if visible and self._applet_mode() == APPLET_MODE_OFF:
            logger.info(f"Applet mode 'off': blocking show request from {source}")
            return

        logger.info(f"WindowVisibilityCoordinator: visibility={visible}, source={source}")

        # Update the actual Qt window
        if visible:
            self.recording_dialog.show()
            logger.info(f"Recording dialog shown (source: {source})")
        else:
            self.recording_dialog.hide()
            logger.info(f"Recording dialog hidden (source: {source})")

        # Update tray menu text
        self.tray_menu_manager.update_dialog_action(visible)

        # Update settings UI (emit signal to QML)
        if self.settings_bridge:
            self.settings_bridge.settingChanged.emit("show_recording_dialog", visible)

    def on_dialog_dismissed(self):
        """Handle recording dialog being manually dismissed"""
        logger.info("WindowVisibilityCoordinator: Dialog manually dismissed")
        if self.app_state:
            self.app_state.set_recording_dialog_visible(False, source="dismissal")
