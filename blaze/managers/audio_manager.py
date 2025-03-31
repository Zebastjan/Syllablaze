"""
Audio Manager for Syllablaze

This module provides a centralized manager for audio recording operations,
reducing code duplication and improving maintainability.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class AudioManager(QObject):
    """Manager class for audio recording operations"""
    
    # Define signals
    volume_changing = pyqtSignal(float)  # Signal for volume level updates
    recording_completed = pyqtSignal(object)  # Signal for completed recording (with audio data)
    recording_failed = pyqtSignal(str)  # Signal for recording errors
    
    def __init__(self, settings):
        """Initialize the audio manager
        
        Parameters:
        -----------
        settings : Settings
            Application settings
        """
        super().__init__()
        self.settings = settings
        self.recorder = None
        self.is_recording = False
    
    def initialize(self):
        """Initialize the audio recorder
        
        Returns:
        --------
        bool
            True if initialization was successful, False otherwise
        """
        try:
            from blaze.recorder import AudioRecorder
            
            # Create recorder instance
            self.recorder = AudioRecorder()
            
            # Connect signals
            self.recorder.volume_changing.connect(self.volume_changing)
            self.recorder.recording_completed.connect(self.recording_completed)
            self.recorder.recording_failed.connect(self.recording_failed)
            
            logger.info("Audio manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio manager: {e}")
            return False
    
    def start_recording(self):
        """Start audio recording
        
        Returns:
        --------
        bool
            True if recording started successfully, False otherwise
        """
        if not self.recorder:
            logger.error("Cannot start recording: recorder not initialized")
            self.recording_failed.emit("Recorder not initialized")
            return False
            
        if self.is_recording:
            logger.warning("Recording already in progress")
            return True
            
        try:
            self.recorder.start_recording()
            self.is_recording = True
            logger.info("Recording started")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording_failed.emit(f"Failed to start recording: {str(e)}")
            return False
    
    def stop_recording(self):
        """Stop audio recording
        
        Returns:
        --------
        bool
            True if recording stopped successfully, False otherwise
        """
        if not self.recorder:
            logger.error("Cannot stop recording: recorder not initialized")
            return False
            
        if not self.is_recording:
            logger.warning("No recording in progress")
            return True
            
        try:
            self.recorder._stop_recording()
            self.is_recording = False
            logger.info("Recording stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            self.recording_failed.emit(f"Failed to stop recording: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up audio resources
        
        Returns:
        --------
        bool
            True if cleanup was successful, False otherwise
        """
        if not self.recorder:
            return True
            
        try:
            # Stop recording if in progress
            if self.is_recording:
                self.stop_recording()
                
            # Clean up recorder
            self.recorder.cleanup()
            self.recorder = None
            logger.info("Audio manager cleaned up")
            return True
        except Exception as e:
            logger.error(f"Failed to clean up audio manager: {e}")
            return False