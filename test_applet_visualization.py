#!/usr/bin/env python3
"""
Quick test to visualize the recording applet with mock audio data.
"""
import sys
import math
from collections import deque
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from blaze.recording_applet import RecordingApplet
from blaze.settings import Settings
from blaze.application_state import ApplicationState


class MockAudioManager(QObject):
    """Mock audio manager for testing."""
    volume_changing = pyqtSignal(float)
    audio_samples_changing = pyqtSignal(object)

    def __init__(self):
        super().__init__()


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Applet Test Controls")

        # Create mock dependencies
        self.settings = Settings()
        self.app_state = ApplicationState(settings=self.settings)
        self.audio_manager = MockAudioManager()

        # Create the applet
        self.applet = RecordingApplet(
            settings=self.settings,
            app_state=self.app_state,
            audio_manager=self.audio_manager
        )

        # Setup UI
        layout = QVBoxLayout()

        self.toggle_btn = QPushButton("Start Recording")
        self.toggle_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.toggle_btn)

        show_btn = QPushButton("Show Applet")
        show_btn.clicked.connect(self.applet.show)
        layout.addWidget(show_btn)

        hide_btn = QPushButton("Hide Applet")
        hide_btn.clicked.connect(self.applet.hide)
        layout.addWidget(hide_btn)

        self.setLayout(layout)

        # Timer to generate fake audio samples
        self.sample_timer = QTimer()
        self.sample_timer.timeout.connect(self.update_samples)
        self.sample_timer.setInterval(16)  # ~60fps

        self.phase = 0
        self.is_recording = False

    def toggle_recording(self):
        self.is_recording = not self.is_recording

        if self.is_recording:
            self.app_state.start_recording()
            self.toggle_btn.setText("Stop Recording")
            self.sample_timer.start()
        else:
            self.app_state.stop_recording()
            self.toggle_btn.setText("Start Recording")
            self.sample_timer.stop()

    def update_samples(self):
        """Generate fake waveform samples."""
        # Create 128 samples of a sine wave with some noise
        samples = deque(maxlen=128)
        for i in range(128):
            # Mix of different frequencies
            angle = (i / 128.0 + self.phase) * 2 * math.pi
            sample = math.sin(angle * 3) * 0.5 + math.sin(angle * 7) * 0.3
            samples.append(sample)

        # Update phase for animation
        self.phase += 0.05
        if self.phase > 1.0:
            self.phase -= 1.0

        # Send to applet
        self.applet._audio_samples = samples

        # Also update volume (oscillate between 0.2 and 0.8)
        volume = 0.5 + 0.3 * math.sin(self.phase * 2 * math.pi)
        self.applet._current_volume = volume

        # Trigger repaint
        self.applet.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = TestWindow()
    window.show()

    # Show applet immediately
    window.applet.show()

    # Auto-start recording after a short delay to see the visualization
    QTimer.singleShot(500, window.toggle_recording)

    sys.exit(app.exec())
