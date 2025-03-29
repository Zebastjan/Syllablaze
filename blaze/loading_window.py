from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from blaze.constants import APP_NAME, APP_VERSION
from blaze.utils import center_window

class LoadingWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Loading {APP_NAME}")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
        
        layout = QVBoxLayout(self)
        
        # Icon and title
        title_layout = QVBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme('audio-input-microphone').pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(f"Loading {APP_NAME}")
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 10pt; color: #666;")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d99f3;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addWidget(version_label)
        layout.addLayout(title_layout)
        
        # Status message
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)  # Set range from 0 to 100 for percentage
        layout.addWidget(self.progress)
        
        # Center the window on screen
        center_window(self)
        
    def set_status(self, message):
        self.status_label.setText(message)
        
    def set_progress(self, value):
        """Update progress bar with a percentage value (0-100)"""
        if value < 0:
            value = 0
        elif value > 100:
            value = 100
        self.progress.setValue(value)
        self.progress.setFormat(f"{value}%")
        self.progress.setTextVisible(True)