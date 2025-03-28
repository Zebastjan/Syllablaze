from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar,
                             QApplication, QPushButton, QHBoxLayout, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from blaze.volume_meter import VolumeMeter
from blaze.constants import APP_NAME, APP_VERSION
from blaze.settings import Settings

class ProgressWindow(QWidget):
    stop_clicked = pyqtSignal()  # Signal emitted when stop button is clicked

    def __init__(self, title="Recording"):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.CustomizeWindowHint |
                           Qt.WindowType.WindowTitleHint)
        
        # Prevent closing while processing
        self.processing = False
        
        # Get settings
        self.settings = Settings()
        
        # Create main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add app name and version
        app_title = QLabel(f"{APP_NAME} v{APP_VERSION}")
        app_title_font = QFont()
        app_title_font.setBold(True)
        app_title_font.setPointSize(12)
        app_title.setFont(app_title_font)
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(app_title)
        
        # Add settings info
        settings_frame = QFrame()
        settings_frame.setFrameShape(QFrame.Shape.StyledPanel)
        settings_frame.setFrameShadow(QFrame.Shadow.Sunken)
        settings_layout = QVBoxLayout(settings_frame)
        
        # Get current settings
        model_name = self.settings.get('model', 'tiny')
        language = self.settings.get('language', 'auto')
        if language == 'auto':
            language_display = 'Auto-detect'
        else:
            from blaze.constants import VALID_LANGUAGES
            language_display = VALID_LANGUAGES.get(language, language)
        
        # Add settings labels
        settings_layout.addWidget(QLabel(f"Model: {model_name}"))
        settings_layout.addWidget(QLabel(f"Language: {language_display}"))
        settings_layout.addWidget(QLabel("Processing: In-memory (no temp files)"))
        
        layout.addWidget(settings_frame)
        
        # Add status label
        self.status_label = QLabel("Recording...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Create volume meter
        self.volume_meter = VolumeMeter()
        layout.addWidget(self.volume_meter)
        
        # Add progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Add stop button with double height
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setMinimumHeight(60)  # Make button twice as tall
        stop_button_font = QFont()
        stop_button_font.setBold(True)
        stop_button_font.setPointSize(11)
        self.stop_button.setFont(stop_button_font)
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_button)
        
        # Set window size
        self.setFixedSize(400, 320)  # Increased size to accommodate new elements
        
        # Center the window
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )
    
    def closeEvent(self, event):
        if self.processing:
            event.ignore()
        else:
            super().closeEvent(event)
    
    def set_status(self, text):
        self.status_label.setText(text)
    
    def update_volume(self, value):
        self.volume_meter.set_value(value)
    
    def set_processing_mode(self):
        """Switch UI to processing mode"""
        self.processing = True
        self.volume_meter.hide()
        self.stop_button.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing audio with Whisper...")
        self.setFixedHeight(220)  # Adjusted for new layout
    
    def set_recording_mode(self):
        """Switch back to recording mode"""
        self.processing = False
        self.volume_meter.show()
        self.progress_bar.hide()
        self.stop_button.show()
        self.status_label.setText("Recording...")
        self.setFixedHeight(320)  # Adjusted for new layout
        
    def update_progress(self, percent):
        """Update the progress bar with a percentage value"""
        if self.processing and self.progress_bar.isVisible():
            self.progress_bar.setValue(percent)