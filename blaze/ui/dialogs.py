"""
Dialog utilities for model management
"""

import re
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from blaze.models.registry import ModelRegistry


class DialogUtils:
    """Utility class for dialog operations"""

    @staticmethod
    def confirm_download(model_name, size_mb):
        """Show confirmation dialog before downloading a model"""
        # Get model information from the registry
        model_info = ModelRegistry.get_model_info(model_name)
        if not model_info:
            model_info = {"size_mb": size_mb, "description": f"{model_name} model"}

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(f"Download Faster Whisper model '{model_name}'?")
        msg.setInformativeText(
            f"This will download approximately {model_info['size_mb']} MB of data.\n{model_info['description']}"
        )

        msg.setWindowTitle("Confirm Download")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return msg.exec() == QMessageBox.StandardButton.Yes

    @staticmethod
    def confirm_delete(model_name, size_mb):
        """Show confirmation dialog before deleting a model"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Delete Faster Whisper model '{model_name}'?")
        msg.setInformativeText(
            f"This will free up {size_mb:.1f} MB of disk space.\n"
            f"You will need to download this model again if you want to use it in the future."
        )
        msg.setWindowTitle("Confirm Deletion")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return msg.exec() == QMessageBox.StandardButton.Yes


# Backward compatibility functions
def confirm_download(model_name, size_mb):
    """Show confirmation dialog before downloading a model (backward compatibility)"""
    return DialogUtils.confirm_download(model_name, size_mb)


def confirm_delete(model_name, size_mb):
    """Show confirmation dialog before deleting a model (backward compatibility)"""
    return DialogUtils.confirm_delete(model_name, size_mb)


class ModelDownloadDialog(QDialog):
    """Dialog to show model download progress"""

    def __init__(self, model_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Downloading {model_name} model")
        self.setFixedSize(400, 180)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
        )

        layout = QVBoxLayout(self)

        # Status label
        self.status_label = QLabel(f"Preparing to download {model_name} model...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Size label
        self.size_label = QLabel("Downloaded: 0 MB / 0 MB")
        layout.addWidget(self.size_label)

        # Time remaining label
        self.time_remaining_label = QLabel("Estimating time remaining...")
        layout.addWidget(self.time_remaining_label)

        # Current progress values
        self.current_value = 0
        self.max_value = 100
        self.downloaded_mb = 0
        self.total_mb = 0

    def set_progress(self, value, maximum):
        """Set progress value"""
        self.current_value = value
        self.max_value = maximum
        self.progress_bar.setValue(value)

        # Extract download size from status text if available
        if (
            hasattr(self, "downloaded_mb")
            and hasattr(self, "total_mb")
            and self.total_mb > 0
        ):
            self.size_label.setText(
                f"Downloaded: {self.downloaded_mb:.1f} MB / {self.total_mb:.1f} MB"
            )

    def set_status(self, text):
        """Update status text and extract size information if available"""
        self.status_label.setText(text)

        # Try to extract download size information from status text
        size_match = re.search(r"(\d+\.\d+)MB\s*/\s*(\d+\.\d+)MB", text)
        if size_match:
            self.downloaded_mb = float(size_match.group(1))
            self.total_mb = float(size_match.group(2))
            self.size_label.setText(
                f"Downloaded: {self.downloaded_mb:.1f} MB / {self.total_mb:.1f} MB"
            )

    def set_time_remaining(self, seconds):
        """Update time remaining"""
        if seconds < 0:
            self.time_remaining_label.setText("Estimating time remaining...")
        else:
            minutes, secs = divmod(seconds, 60)
            self.time_remaining_label.setText(
                f"Time remaining: {int(minutes)}m {int(secs)}s"
            )
