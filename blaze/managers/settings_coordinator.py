from PyQt6.QtCore import QObject
import logging

logger = logging.getLogger(__name__)


class SettingsCoordinator(QObject):
    """Coordinates settings changes to appropriate components"""

    def __init__(self, recording_dialog, app_state):
        """Initialize settings coordinator

        Args:
            recording_dialog: RecordingDialogManager instance
            app_state: ApplicationState instance
        """
        super().__init__()
        self.recording_dialog = recording_dialog
        self.app_state = app_state
        self.progress_window = None  # Set later when created

    def set_progress_window(self, progress_window):
        """Set progress window reference after creation"""
        self.progress_window = progress_window

    def on_setting_changed(self, key, value):
        """Handle setting changes from settings window

        Args:
            key (str): Setting key that changed
            value: New value for the setting
        """
        logger.info(f"SettingsCoordinator: Setting changed: {key} = {value}")

        if key == "show_recording_dialog":
            if self.recording_dialog and self.app_state:
                # Convert value to boolean (QML might send various types)
                visible = bool(value) if value is not None else True
                # Update ApplicationState (which will trigger visibility changes)
                self.app_state.set_recording_dialog_visible(visible, source="settings_ui")

        elif key == "show_progress_window":
            # Store the setting for use when showing progress window
            logger.info(f"Progress window visibility setting changed to: {value}")
            # The actual show/hide will be handled in toggle_recording based on this setting

        elif key == "recording_dialog_always_on_top":
            # Update the recording dialog's always-on-top property
            if self.recording_dialog:
                always_on_top = bool(value) if value is not None else True
                self.recording_dialog.update_always_on_top(always_on_top)

        elif key == "progress_window_always_on_top":
            # Update the progress window's always-on-top property
            if self.progress_window:
                always_on_top = bool(value) if value is not None else True
                self.progress_window.update_always_on_top(always_on_top)
                logger.info(f"Updated progress window always-on-top to: {always_on_top}")
