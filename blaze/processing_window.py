from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from blaze.utils import center_window

class ProcessingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Processing Recording")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add status label
        self.status_label = QLabel("Transcribing audio...")
        layout.addWidget(self.status_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Set window size
        self.setFixedSize(300, 100)
        
        # Center the window
        center_window(self)
    
    def set_status(self, text):
        self.status_label.setText(text) 