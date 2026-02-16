from PyQt6.QtCore import QObject
import logging

logger = logging.getLogger(__name__)


class WindowVisibilityCoordinator(QObject):
    """Coordinates window visibility across app state, UI, and tray menu"""

    def __init__(self, recording_dialog, app_state, tray_menu_manager, settings_bridge):
        """Initialize window visibility coordinator

        Args:
            recording_dialog: RecordingDialogManager instance
            app_state: ApplicationState instance
            tray_menu_manager: TrayMenuManager instance
            settings_bridge: SettingsBridge from settings window
        """
        super().__init__()
        self.recording_dialog = recording_dialog
        self.app_state = app_state
        self.tray_menu_manager = tray_menu_manager
        self.settings_bridge = settings_bridge

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

        Args:
            visible (bool): True to show dialog, False to hide
            source (str): Source of the change (startup, settings_ui, tray_menu, dismissal)
        """
        if not self.recording_dialog:
            logger.warning(f"Cannot update dialog visibility: dialog not initialized (source: {source})")
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
