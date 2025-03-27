from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
import whisper
import os
import logging
import time
from blaze.settings import Settings
from blaze.constants import DEFAULT_WHISPER_MODEL
from blaze.whisper_model_manager import get_model_info
logger = logging.getLogger(__name__)

class TranscriptionWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, model, audio_file):
        super().__init__()
        self.model = model
        self.audio_file = audio_file
        
    def run(self):
        try:
            if not os.path.exists(self.audio_file):
                raise FileNotFoundError(f"Audio file not found: {self.audio_file}")
                
            self.progress.emit("Loading audio file...")
            self.progress_percent.emit(10)
            
            # Load and transcribe
            self.progress.emit("Processing audio with Whisper...")
            self.progress_percent.emit(30)
            
            # Simulate progress updates during transcription
            def progress_callback(progress):
                # Convert progress to percentage (30-90%)
                percent = int(30 + progress * 60)
                self.progress_percent.emit(percent)
                self.progress.emit(f"Transcribing... {percent}%")
            
            result = self.model.transcribe(
                self.audio_file,
                fp16=False,
                language='en'
            )
            
            text = result["text"].strip()
            if not text:
                raise ValueError("No text was transcribed")
                
            self.progress.emit("Transcription completed!")
            self.progress_percent.emit(100)
            logger.info(f"Transcribed text: {text[:100]}...")
            self.finished.emit(text)
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.error.emit(f"Transcription failed: {str(e)}")
            self.finished.emit("")
        finally:
            # Clean up the temporary file
            try:
                if os.path.exists(self.audio_file):
                    os.remove(self.audio_file)
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {e}")

class WhisperTranscriber(QObject):
    transcription_progress = pyqtSignal(str)
    transcription_progress_percent = pyqtSignal(int)
    transcription_finished = pyqtSignal(str)
    transcription_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.worker = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.load_model()
        
    def load_model(self):
        try:
            settings = Settings()
            model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
            logger.info(f"Loading Whisper model: {model_name}")
            
            # Check if model is downloaded
            model_info, _ = get_model_info()
            if model_name in model_info and not model_info[model_name]['is_downloaded']:
                error_msg = f"Model '{model_name}' is not downloaded. Please download it in Settings."
                logger.error(error_msg)
                self.transcription_error.emit(error_msg)
                raise ValueError(error_msg)
            
            # Redirect whisper's logging to our logger
            import logging as whisper_logging
            whisper_logging.getLogger("whisper").setLevel(logging.WARNING)
            
            self.model = whisper.load_model(model_name)
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
        
    def _cleanup_worker(self):
        if self.worker:
            if self.worker.isFinished():
                self.worker.deleteLater()
                self.worker = None
                
    def transcribe(self, audio_file):
        """Transcribe audio file using Whisper"""
        try:
            settings = Settings()
            language = settings.get('language', 'auto')
            
            # Emit progress update
            self.transcription_progress.emit("Processing audio...")
            
            # Run transcription with language setting
            result = self.model.transcribe(
                audio_file,
                fp16=False,
                language=None if language == 'auto' else language
            )
            
            text = result["text"].strip()
            if not text:
                raise ValueError("No text was transcribed")
                
            self.transcription_progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: {text[:100]}...")
            self.transcription_finished.emit(text)
            
            # Clean up the temporary file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {e}")
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.transcription_error.emit(str(e))

    def transcribe_file(self, audio_file):
        if self.worker and self.worker.isRunning():
            logger.warning("Transcription already in progress")
            return
            
        # Emit initial progress status before starting worker
        self.transcription_progress.emit("Starting transcription...")
        self.transcription_progress_percent.emit(5)
            
        self.worker = TranscriptionWorker(self.model, audio_file)
        self.worker.finished.connect(self.transcription_finished)
        self.worker.progress.connect(self.transcription_progress)
        self.worker.progress_percent.connect(self.transcription_progress_percent)
        self.worker.error.connect(self.transcription_error)
        self.worker.finished.connect(lambda: self._cleanup_timer.start(1000))
        self.worker.start()