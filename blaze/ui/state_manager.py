"""
UI State Management for Syllablaze

This module provides abstractions for managing UI states, including:
- Base UIState class
- RecordingState for recording mode
- ProcessingState for processing mode
"""

import logging

logger = logging.getLogger(__name__)


class UIState:
    """Base class for UI states"""

    def __init__(self, window):
        self.window = window

    def enter(self):
        """Called when entering this state"""
        pass

    def exit(self):
        """Called when exiting this state"""
        pass

    def update(self, **kwargs):
        """Update the state with new data"""
        pass


class RecordingState(UIState):
    """State for recording mode"""

    def enter(self):
        """Set up the UI for recording mode"""
        logger.info("Entering recording state")
        self.window.processing = False
        self.window.volume_meter.show()
        self.window.progress_bar.hide()
        self.window.stop_button.show()
        self.window.status_label.setText("Recording...")
        self.window.setFixedHeight(160)

    def update(self, volume=None, status=None, **kwargs):
        """Update the recording state"""
        if volume is not None:
            self.window.volume_meter.set_value(volume)
        if status is not None:
            self.window.status_label.setText(status)


class ProcessingState(UIState):
    """State for processing mode"""

    def enter(self):
        """Set up the UI for processing mode"""
        logger.info("Entering processing state")
        self.window.processing = True
        self.window.volume_meter.hide()
        self.window.stop_button.hide()
        self.window.progress_bar.show()
        self.window.progress_bar.setValue(0)
        self.window.status_label.setText("Processing audio with Whisper...")
        self.window.setFixedHeight(110)

    def update(self, progress=None, status=None, **kwargs):
        """Update the processing state"""
        if progress is not None:
            self.window.progress_bar.setValue(progress)
        if status is not None:
            self.window.status_label.setText(status)
