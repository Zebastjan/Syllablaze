from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
import whisper
import os
import logging
import time
from blaze.settings import Settings
from blaze.constants import DEFAULT_WHISPER_MODEL
from blaze.utils.whisper_model_manager import WhisperModelManager
logger = logging.getLogger(__name__)

class TranscriptionWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, model, audio_data):
        super().__init__()
        self.model = model
        self.audio_data = audio_data
        self.settings = Settings()
        self.language = self.settings.get('language', 'auto')
        
    def run(self):
        try:
            self.progress.emit("Processing audio...")
            self.progress_percent.emit(10)
            
            # Transcribe directly from memory
            self.progress.emit("Processing audio with Whisper...")
            self.progress_percent.emit(30)
            
            # Simulate progress updates during transcription
            def progress_callback(progress):
                # Convert progress to percentage (30-90%)
                percent = int(30 + progress * 60)
                self.progress_percent.emit(percent)
                self.progress.emit(f"Transcribing... {percent}%")
            
            # Log the language being used for transcription
            lang_str = "auto-detect" if self.language == 'auto' else self.language
            logger.info(f"Transcribing with language: {lang_str}")
            
            result = self.model.transcribe(
                self.audio_data,
                fp16=False,
                language=None if self.language == 'auto' else self.language
            )
            
            text = result["text"].strip()
            if not text:
                raise ValueError("No text was transcribed")
                
            self.progress.emit("Transcription completed!")
            self.progress_percent.emit(100)
            logger.info(f"Transcribed text: [{text}]")
            self.finished.emit(text)
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.error.emit(f"Transcription failed: {str(e)}")
            self.finished.emit("")

class WhisperTranscriber(QObject):
    transcription_progress = pyqtSignal(str)
    transcription_progress_percent = pyqtSignal(int)
    transcription_finished = pyqtSignal(str)
    transcription_error = pyqtSignal(str)
    model_changed = pyqtSignal(str)  # Signal to notify when model is changed
    language_changed = pyqtSignal(str)  # Signal to notify when language is changed
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.worker = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.settings = Settings()
        self.current_language = self.settings.get('language', 'auto')
        self.model_manager = WhisperModelManager(self.settings)
        self.load_model()
        
    def load_model(self):
        """Load the Whisper model based on current settings"""
        try:
            model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
            
            # Store the current model name for reference
            self.current_model_name = model_name
            
            # Load the model using the model manager
            self.model = self.model_manager.load_model(model_name)
            
            # Update and log the current language setting
            self.current_language = self.settings.get('language', 'auto')
            lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
            logger.info(f"Current language setting: {lang_str}")
            
            # Log to console if running in terminal
            print(f"Model loaded: {model_name}, Language: {lang_str}")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            print(f"Error loading model: {e}")
            self.transcription_error.emit(f"Failed to load Whisper model: {e}")
            raise
            
    def reload_model_if_needed(self):
        """Check if model needs to be reloaded due to settings changes"""
        model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
        
        # Check if the model has changed
        if not hasattr(self, 'current_model_name') or model_name != self.current_model_name:
            logger.info(f"Model changed from {getattr(self, 'current_model_name', 'None')} to {model_name}, reloading...")
            self.load_model()
            return True
        
        return False
        
    def update_model(self, model_name=None):
        """Update the model based on settings or provided model name"""
        if model_name is None:
            model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
        
        if not hasattr(self, 'current_model_name') or model_name != self.current_model_name:
            self.load_model()
            self.model_changed.emit(model_name)
            return True
        else:
            logger.info(f"Model {model_name} is already loaded, no change needed")
            print(f"Model {model_name} is already loaded, no change needed")
            return False
            
    def update_language(self, language=None):
        """Update the language setting"""
        import sys
        
        if language is None:
            language = self.settings.get('language', 'auto')
            
        if language != self.current_language:
            old_language = self.current_language
            self.current_language = language
            self.language_changed.emit(language)
            
            # Force update of any tray icons
            app = QApplication.instance()
            
            # First update all widgets with update_tooltip method
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'update_tooltip'):
                    widget.update_tooltip()
            
            # Then specifically look for system tray icons
            for widget in app.topLevelWidgets():
                # Check if this widget is a QSystemTrayIcon
                if isinstance(widget, QSystemTrayIcon) and hasattr(widget, 'update_tooltip'):
                    widget.update_tooltip()
                
                # Also search through all child widgets recursively
                tray_icons = widget.findChildren(QSystemTrayIcon)
                for tray_icon in tray_icons:
                    if hasattr(tray_icon, 'update_tooltip'):
                        tray_icon.update_tooltip()
            
            return True
        else:
            logger.info(f"Language {language} is already set, no change needed")
            print(f"Language {language} is already set, no change needed", flush=True)
            sys.stdout.flush()
            return False
        
    def _cleanup_worker(self):
        if self.worker:
            if self.worker.isFinished():
                self.worker.deleteLater()
                self.worker = None
                
    def _prepare_for_transcription(self):
        """Prepare for transcription by checking model and language settings"""
        # Check if model needs to be reloaded due to settings changes
        model_reloaded = self.reload_model_if_needed()
        
        # Check if language has changed
        current_language = self.settings.get('language', 'auto')
        language_changed = False
        if current_language != self.current_language:
            logger.info(f"Language changed from {self.current_language} to {current_language}, updating...")
            self.current_language = current_language
            language_changed = True
        
        # Log the language being used for transcription
        lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
        logger.info(f"Transcription using language: {lang_str}")
        logger.info(f"Transcription using model: {self.current_model_name}")
        
        return model_reloaded, language_changed, lang_str

    def transcribe(self, audio_data):
        """Transcribe audio data directly from memory"""
        try:
            # Prepare for transcription
            _, _, lang_str = self._prepare_for_transcription()
            
            # Emit progress update
            self.transcription_progress.emit("Processing audio...")
            
            print(f"Transcribing with model: {self.current_model_name}, language: {lang_str}")
            
            # Run transcription with language setting
            result = self.model.transcribe(
                audio_data,
                fp16=False,
                language=None if self.current_language == 'auto' else self.current_language
            )
            
            text = result["text"].strip()
            if not text:
                raise ValueError("No text was transcribed")
                
            self.transcription_progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: [{text}]")
            self.transcription_finished.emit(text)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.transcription_error.emit(str(e))

    def transcribe_audio(self, normalized_audio_data):
        """
        Transcribe normalized audio data from memory using Whisper model
        
        Parameters:
        -----------
        normalized_audio_data : np.ndarray
            Pre-processed audio data as float32 NumPy array with values normalized
            to range [-1.0, 1.0]. The array should be mono (single channel) and
            sampled at 16kHz for optimal Whisper performance.
            
        Notes:
        ------
        - This method starts an asynchronous transcription process
        - Progress updates are emitted via signals:
          * transcription_progress(str)
          * transcription_progress_percent(int)
          * transcription_finished(str) when finished
          * transcription_error(str) on errors
        """
        if self.worker and self.worker.isRunning():
            logger.warning("Transcription already in progress")
            return
        
        # Prepare for transcription
        model_reloaded, language_changed, lang_str = self._prepare_for_transcription()
        
        # Log changes if any occurred
        if model_reloaded:
            logger.info("Model was reloaded due to settings change before transcription")
            print(f"Model reloaded to: {self.current_model_name}")
            
        if language_changed:
            print(f"Language changed to: {self.current_language}")
        
        # Emit initial progress status before starting worker
        self.transcription_progress.emit("Starting transcription...")
        self.transcription_progress_percent.emit(5)
        
        print(f"Transcribing audio with model: {self.current_model_name}, language: {lang_str}")
        
        self.worker = TranscriptionWorker(self.model, normalized_audio_data)
        # Make sure the worker uses the current language setting
        self.worker.language = self.current_language
        self.worker.finished.connect(self.transcription_finished)
        self.worker.progress.connect(self.transcription_progress)
        self.worker.progress_percent.connect(self.transcription_progress_percent)
        self.worker.error.connect(self.transcription_error)
        self.worker.finished.connect(lambda: self._cleanup_timer.start(1000))
        self.worker.start()