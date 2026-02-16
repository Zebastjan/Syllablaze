from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject


class TrayMenuManager(QObject):
    """Manages system tray menu creation and state updates"""

    def __init__(self):
        super().__init__()
        self.record_action = None
        self.settings_action = None
        self.dialog_action = None
        self.menu = None

    def create_menu(self, toggle_recording_callback, toggle_settings_callback,
                   toggle_dialog_callback, quit_callback):
        """Create and return the tray context menu

        Args:
            toggle_recording_callback: Handler for Start/Stop Recording
            toggle_settings_callback: Handler for Settings
            toggle_dialog_callback: Handler for Show/Hide Recording Dialog
            quit_callback: Handler for Quit

        Returns:
            QMenu: Configured context menu
        """
        self.menu = QMenu()

        # Recording action
        self.record_action = QAction("Start Recording", self.menu)
        self.record_action.triggered.connect(toggle_recording_callback)
        self.menu.addAction(self.record_action)

        # Settings action
        self.settings_action = QAction("Settings", self.menu)
        self.settings_action.triggered.connect(toggle_settings_callback)
        self.menu.addAction(self.settings_action)

        # Recording dialog toggle action
        self.dialog_action = QAction("Show Recording Dialog", self.menu)
        self.dialog_action.triggered.connect(toggle_dialog_callback)
        self.menu.addAction(self.dialog_action)

        # Separator
        self.menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(quit_callback)
        self.menu.addAction(quit_action)

        return self.menu

    def update_recording_action(self, is_recording):
        """Update recording action text based on state

        Args:
            is_recording (bool): True if currently recording
        """
        if self.record_action:
            text = "Stop Recording" if is_recording else "Start Recording"
            self.record_action.setText(text)

    def update_dialog_action(self, is_visible):
        """Update dialog action text based on visibility

        Args:
            is_visible (bool): True if dialog is visible
        """
        if self.dialog_action:
            text = "Hide Recording Dialog" if is_visible else "Show Recording Dialog"
            self.dialog_action.setText(text)
