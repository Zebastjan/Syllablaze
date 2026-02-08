"""
Transcription Manager for Syllablaze

This module provides a centralized manager for transcription operations,
reducing code duplication and improving maintainability.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from blaze.constants import (
    DEFAULT_WHISPER_MODEL, DEFAULT_BEAM_SIZE, DEFAULT_VAD_FILTER, 
    DEFAULT_WORD_TIMESTAMPS
)

logger = logging.getLogger(__name__)

class TranscriptionManager(QObject):
    """Manager class for transcription operations"""
    
    # Define signals
    transcription_progress = pyqtSignal(str)  # Signal for progress updates
    transcription_progress_percent = pyqtSignal(int)  # Signal for progress percentage
    transcription_finished = pyqtSignal(str)  # Signal for completed transcription
    transcription_error = pyqtSignal(str)  # Signal for transcription errors
    model_changed = pyqtSignal(str)  # Signal for model changes
    language_changed = pyqtSignal(str)  # Signal for language changes
    
    def __init__(self, settings):
        """Initialize the transcription manager
        
        Parameters:
        -----------
        settings : Settings
            Application settings
        """
        super().__init__()
        self.settings = settings
        self.transcriber = None
        self.current_model = None
        self.current_language = None
    
    def configure_optimal_settings(self):
        """Configure optimal settings for Faster Whisper based on hardware
        
        Returns:
        --------
        bool
            True if configuration was successful, False otherwise
        """
        try:
            # Check if this is the first run with Faster Whisper settings
            if self.settings.get('compute_type') is None:
                # Check for GPU support
                try:
                    import torch
                    has_gpu = torch.cuda.is_available()
                except ImportError:
                    has_gpu = False
                except Exception:
                    has_gpu = False
                    
                if has_gpu:
                    # Configure for GPU
                    self.settings.set('device', 'cuda')
                    self.settings.set('compute_type', 'float16')  # Good balance of speed and accuracy
                else:
                    # Configure for CPU
                    self.settings.set('device', 'cpu')
                    self.settings.set('compute_type', 'int8')  # Best performance on CPU
                    
                # Set other defaults
                self.settings.set('beam_size', DEFAULT_BEAM_SIZE)
                self.settings.set('vad_filter', DEFAULT_VAD_FILTER)
                self.settings.set('word_timestamps', DEFAULT_WORD_TIMESTAMPS)
                
                logger.info("Faster Whisper configured with optimal settings for your hardware.")
                print("Faster Whisper configured with optimal settings for your hardware.")
            
            return True
        except Exception as e:
            logger.error(f"Failed to configure optimal settings: {e}")
            return False
    
    def initialize(self):
        """Initialize the transcriber
        
        Returns:
        --------
        bool
            True if initialization was successful, False otherwise
        """
        try:
            from blaze.transcriber import WhisperTranscriber
            
            # Configure optimal settings
            self.configure_optimal_settings()
            
            # Create transcriber instance
            self.transcriber = WhisperTranscriber()
            
            # Connect signals
            self.transcriber.transcription_progress.connect(self.transcription_progress)
            self.transcriber.transcription_progress_percent.connect(self.transcription_progress_percent)
            self.transcriber.transcription_finished.connect(self.transcription_finished)
            self.transcriber.transcription_error.connect(self.transcription_error)
            self.transcriber.model_changed.connect(self.model_changed)
            self.transcriber.language_changed.connect(self.language_changed)
            
            # Store current model and language
            self.current_model = self.settings.get('model', DEFAULT_WHISPER_MODEL)
            self.current_language = self.settings.get('language', 'auto')
            
            logger.info(f"Transcription manager initialized with model: {self.current_model}, language: {self.current_language}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize transcription manager: {e}")
            self._create_dummy_transcriber()
            return False
    
    def _create_dummy_transcriber(self):
        """Create a dummy transcriber when initialization fails"""
        # Create a dummy transcriber that will show a message when used
        class DummyTranscriber(QObject):
            # Define signals at the class level
            transcription_progress = pyqtSignal(str)
            transcription_progress_percent = pyqtSignal(int)
            transcription_finished = pyqtSignal(str)
            transcription_error = pyqtSignal(str)
            model_changed = pyqtSignal(str)
            language_changed = pyqtSignal(str)
            
            def __init__(self):
                super().__init__()  # Initialize the QObject base class
                self.model = None
                
            def transcribe_audio(self, *args, **kwargs):
                self.transcription_error.emit("No models downloaded. Please go to Settings to download a model.")
                
            def transcribe(self, *args, **kwargs):
                self.transcription_error.emit("No models downloaded. Please go to Settings to download a model.")
                
            def update_model(self, *args, **kwargs):
                return False
                
            def update_language(self, *args, **kwargs):
                return False
        
        # Create a dummy transcriber with the same interface
        self.transcriber = DummyTranscriber()
        
        # Connect signals
        self.transcriber.transcription_progress.connect(self.transcription_progress)
        self.transcriber.transcription_progress_percent.connect(self.transcription_progress_percent)
        self.transcriber.transcription_finished.connect(self.transcription_finished)
        self.transcriber.transcription_error.connect(self.transcription_error)
        
        logger.warning("Created dummy transcriber due to initialization failure")
    
    def transcribe_audio(self, audio_data):
        """Transcribe audio data
        
        Parameters:
        -----------
        audio_data : numpy.ndarray
            Audio data to transcribe
            
        Returns:
        --------
        bool
            True if transcription started successfully, False otherwise
        """
        if not self.transcriber:
            logger.error("Cannot transcribe: transcriber not initialized")
            self.transcription_error.emit("Transcriber not initialized")
            return False
            
        try:
            self.transcriber.transcribe_audio(audio_data)
            return True
        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            self.transcription_error.emit(f"Failed to start transcription: {str(e)}")
            return False
    
    def update_model(self, model_name=None):
        """Update the transcription model
        
        Parameters:
        -----------
        model_name : str
            Name of the model to use (optional)
            
        Returns:
        --------
        bool
            True if model was updated, False otherwise
        """
        if not self.transcriber:
            logger.error("Cannot update model: transcriber not initialized")
            return False
            
        try:
            # Get model name from settings if not provided
            if model_name is None:
                model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
                
            # Update model
            result = self.transcriber.update_model(model_name)
            
            if result:
                self.current_model = model_name
                logger.info(f"Model updated to: {model_name}")
                
            return result
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
            return False
    
    def update_language(self, language=None):
        """Update the transcription language
        
        Parameters:
        -----------
        language : str
            Language code to use (optional)
            
        Returns:
        --------
        bool
            True if language was updated, False otherwise
        """
        if not self.transcriber:
            logger.error("Cannot update language: transcriber not initialized")
            return False
            
        try:
            # Get language from settings if not provided
            if language is None:
                language = self.settings.get('language', 'auto')
                
            # Update language
            result = self.transcriber.update_language(language)
            
            if result:
                self.current_language = language
                logger.info(f"Language updated to: {language}")
                
            return result
        except Exception as e:
            logger.error(f"Failed to update language: {e}")
            return False
    
    def handle_transcription_result(self, text):
        """Handle transcription result
        
        Parameters:
        -----------
        text : str
            Transcribed text
            
        Returns:
        --------
        str
            Processed text
        """
        if not text:
            return ""
            
        try:
            # Copy text to clipboard
            QApplication.clipboard().setText(text)
            
            # Return the text
            return text
        except Exception as e:
            logger.error(f"Failed to process transcription result: {e}")
            return text
    
    def cleanup(self):
        """Clean up transcription resources
        
        Returns:
        --------
        bool
            True if cleanup was successful, False otherwise
        """
        if not self.transcriber:
            return True
            
        try:
            # Wait for worker to finish if running
            if hasattr(self.transcriber, 'worker') and self.transcriber.worker:
                if self.transcriber.worker.isRunning():
                    logger.info("Waiting for transcription worker to finish...")
                    self.transcriber.worker.wait(5000)  # Wait up to 5 seconds

            # Explicitly release model resources (CTranslate2 semaphores, etc.)
            if hasattr(self.transcriber, 'model') and self.transcriber.model is not None:
                logger.info("Releasing Whisper model resources")
                del self.transcriber.model
                self.transcriber.model = None
                import gc
                gc.collect()

            # Clean up transcriber
            self.transcriber = None
            logger.info("Transcription manager cleaned up")
            return True
        except Exception as e:
            logger.error(f"Failed to clean up transcription manager: {e}")
            return False