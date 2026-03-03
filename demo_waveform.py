#!/usr/bin/env python3
"""
Simple demo showing the radial waveform visualization.
Creates a large applet (400x400) and immediately starts animated recording.
"""
import sys
import math
from collections import deque
from PyQt6.QtWidgets import QApplication
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


# Create application
app = QApplication(sys.argv)

# Create mock dependencies
settings = Settings()
app_state = ApplicationState(settings=settings)
audio_manager = MockAudioManager()

# Create the applet at large size
applet = RecordingApplet(
    settings=settings,
    app_state=app_state,
    audio_manager=audio_manager
)

# Make it large and visible
applet.resize(400, 400)
applet.move(100, 100)
applet.show()

# Start recording immediately
app_state.start_recording()

# Animation variables
phase = [0.0]


def update_samples():
    """Generate animated waveform samples."""
    # Create 128 samples of a complex waveform
    samples = deque(maxlen=128)
    for i in range(128):
        # Mix multiple sine waves for interesting pattern
        angle = (i / 128.0 + phase[0]) * 2 * math.pi
        sample = (
            math.sin(angle * 3) * 0.4
            + math.sin(angle * 7) * 0.3
            + math.sin(angle * 2) * 0.2
        )
        samples.append(sample)

    # Update phase for animation
    phase[0] += 0.03
    if phase[0] > 1.0:
        phase[0] -= 1.0

    # Send to applet
    applet._audio_samples = samples

    # Oscillating volume
    volume = 0.5 + 0.4 * math.sin(phase[0] * 3 * math.pi)
    applet._current_volume = volume

    # Trigger repaint
    applet.update()


# Start animation timer (60fps)
timer = QTimer()
timer.timeout.connect(update_samples)
timer.setInterval(16)
timer.start()

print("Radial waveform visualization demo running...")
print("- Applet size: 400x400")
print("- 36 radial bars animated at 60fps")
print("- Colors: green → yellow → red based on volume")
print("- Close the window to exit")

sys.exit(app.exec())
