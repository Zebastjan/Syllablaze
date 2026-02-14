"""
Audio Manager for Syllablaze

This module provides a centralized manager for audio recording operations,
reducing code duplication and improving maintainability.
"""

import logging
import time
from PyQt6.QtCore import QObject, pyqtSignal
from blaze.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)

class AudioManager(QObject):
    """Manager class for audio recording operations"""
    
    # Define signals
    volume_changing = pyqtSignal(float)  # Signal for volume level updates
    audio_samples_changing = pyqtSignal(list)  # Signal for audio waveform samples
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
            self.recorder.audio_samples_changing.connect(self.audio_samples_changing)
            self.recorder.recording_completed.connect(self._on_recording_completed)
            self.recorder.recording_failed.connect(self.recording_failed)
            
            logger.info("Audio manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio manager: {e}")
            return False
    
    def _on_recording_completed(self, audio_data):
        """Handle the completed recording signal from the recorder
        
        Parameters:
        -----------
        audio_data : numpy.ndarray
            Processed audio data from the recorder
        """
        # We can simply pass through the audio data, or add additional processing if needed
        self.recording_completed.emit(audio_data)
    
    def start_recording(self):
        """Start audio recording with improved error handling
        
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
            # Check if recorder is ready
            if not hasattr(self.recorder, 'start_recording'):
                logger.error("Recorder object does not have start_recording method")
                self.recording_failed.emit("Invalid recorder object")
                return False
                
            # Start recording with timeout protection
            start_time = time.time()
            self.recorder.start_recording()
            
            # Verify recording started within reasonable time
            if time.time() - start_time > 2.0:  # More than 2 seconds is suspicious
                logger.warning("Recording start took unusually long time")
                
            self.is_recording = True
            logger.info("Recording started")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording_failed.emit(f"Failed to start recording: {str(e)}")
            return False
    
    def stop_recording(self):
        """Stop audio recording with improved error handling
        
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
            # Check if recorder is ready
            if not hasattr(self.recorder, '_stop_recording'):
                logger.error("Recorder object does not have _stop_recording method")
                self.recording_failed.emit("Invalid recorder object")
                return False
                
            # Stop recording with timeout protection
            start_time = time.time()
            self.recorder._stop_recording()
            
            # Verify recording stopped within reasonable time
            if time.time() - start_time > 2.0:  # More than 2 seconds is suspicious
                logger.warning("Recording stop took unusually long time")
                
            self.is_recording = False
            logger.info("Recording stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            self.recording_failed.emit(f"Failed to stop recording: {str(e)}")
            return False
    
    def save_audio_to_file(self, audio_data, filename):
        """Save audio data to a file
        
        Parameters:
        -----------
        audio_data : numpy.ndarray
            Audio data to save
        filename : str
            Path to save the audio file
            
        Returns:
        --------
        bool
            True if saving was successful, False otherwise
        """
        try:
            # Use AudioProcessor to save the file
            from blaze.constants import WHISPER_SAMPLE_RATE
            
            result = AudioProcessor.save_to_wav(
                audio_data, 
                filename, 
                WHISPER_SAMPLE_RATE, 
                channels=1
            )
            
            if result:
                logger.info(f"Audio saved to {filename}")
            else:
                logger.error(f"Failed to save audio to {filename}")
                
            return result
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
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
