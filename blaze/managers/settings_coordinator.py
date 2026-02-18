from PyQt6.QtCore import QObject
from blaze.constants import (
    APPLET_MODE_OFF, APPLET_MODE_PERSISTENT, APPLET_MODE_POPUP,
    POPUP_STYLE_NONE, POPUP_STYLE_TRADITIONAL, POPUP_STYLE_APPLET,
)
import logging

logger = logging.getLogger(__name__)


class SettingsCoordinator(QObject):
    """Coordinates settings changes to appropriate components"""

    def __init__(self, recording_dialog, app_state, settings=None):
        """Initialize settings coordinator

        Args:
            recording_dialog: RecordingDialogManager instance
            app_state: ApplicationState instance
            settings: Settings instance (needed for popup_style derivation)
        """
        super().__init__()
        self.recording_dialog = recording_dialog
        self.app_state = app_state
        self.settings = settings
        self.progress_window = None  # Set later when created

    def set_progress_window(self, progress_window):
        """Set progress window reference after creation"""
        self.progress_window = progress_window

    def _apply_popup_style(self, popup_style, autohide, settings):
        """Derive and write backend settings from popup_style + applet_autohide."""
        if popup_style == POPUP_STYLE_NONE:
            derived = {
                'show_progress_window': False,
                'show_recording_dialog': False,
                'applet_mode': APPLET_MODE_OFF,
            }
        elif popup_style == POPUP_STYLE_TRADITIONAL:
            derived = {
                'show_progress_window': True,
                'show_recording_dialog': False,
                'applet_mode': APPLET_MODE_OFF,
            }
        else:  # POPUP_STYLE_APPLET
            derived = {
                'show_progress_window': False,
                'show_recording_dialog': True,
                'applet_mode': APPLET_MODE_POPUP if autohide else APPLET_MODE_PERSISTENT,
            }
        logger.info(f"popup_style={popup_style!r} autohide={autohide} → derived: {derived}")
        for k, v in derived.items():
            settings.set(k, v)
        self._apply_applet_mode(derived['applet_mode'])

    def _apply_applet_mode(self, value):
        """Apply dialog visibility change when applet_mode setting changes."""
        if not self.app_state:
            return
        mode = str(value) if value is not None else APPLET_MODE_POPUP
        logger.info(f"Applet mode changed to: {mode}")
        if mode == APPLET_MODE_PERSISTENT:
            self.app_state.set_recording_dialog_visible(True, source="applet_mode_change")
            # Apply on-all-desktops for persistent mode
            if self.recording_dialog and self.settings:
                on_all = bool(self.settings.get("applet_onalldesktops", True))
                self.recording_dialog.update_on_all_desktops(on_all)
        elif mode == APPLET_MODE_OFF:
            self.app_state.set_recording_dialog_visible(False, source="applet_mode_change")
            if self.recording_dialog:
                self.recording_dialog.update_on_all_desktops(False)
        else:  # APPLET_MODE_POPUP: no immediate change; auto-show on next record start
            if self.recording_dialog:
                self.recording_dialog.update_on_all_desktops(False)

    def _handle_visibility(self, key, value):
        """Handle visibility-related setting changes."""
        if key == "show_recording_dialog":
            if self.recording_dialog and self.app_state:
                visible = bool(value) if value is not None else True
                self.app_state.set_recording_dialog_visible(visible, source="settings_ui")
        elif key == "show_progress_window":
            logger.info(f"Progress window visibility setting changed to: {value}")
        elif key == "recording_dialog_always_on_top":
            if self.recording_dialog:
                self.recording_dialog.update_always_on_top(bool(value) if value is not None else True)
        elif key == "progress_window_always_on_top":
            if self.progress_window:
                always_on_top = bool(value) if value is not None else True
                self.progress_window.update_always_on_top(always_on_top)
                logger.info(f"Updated progress window always-on-top to: {always_on_top}")

    def _handle_popup_style_change(self, key, value):
        """Handle popup_style and applet_autohide changes."""
        if not self.settings:
            return
        if key == "popup_style":
            autohide = self.settings.get('applet_autohide', True)
            self._apply_popup_style(str(value), bool(autohide), self.settings)
        elif key == "applet_autohide":
            popup_style = self.settings.get('popup_style', POPUP_STYLE_APPLET)
            self._apply_popup_style(str(popup_style), bool(value), self.settings)

    def on_setting_changed(self, key, value):
        """Handle setting changes from settings window."""
        logger.info(f"SettingsCoordinator: Setting changed: {key} = {value}")

        if key in ("show_recording_dialog", "show_progress_window",
                   "recording_dialog_always_on_top", "progress_window_always_on_top"):
            self._handle_visibility(key, value)
        elif key == "applet_mode":
            self._apply_applet_mode(value)
        elif key in ("popup_style", "applet_autohide"):
            self._handle_popup_style_change(key, value)
        elif key == "applet_onalldesktops":
            if self.recording_dialog and self.settings:
                mode = self.settings.get("applet_mode", APPLET_MODE_POPUP)
                if mode == APPLET_MODE_PERSISTENT:
                    self.recording_dialog.update_on_all_desktops(bool(value))
