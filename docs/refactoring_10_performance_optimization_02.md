# Performance Optimization: Model Loading

## 10.2. Inefficient Model Loading

**Issue:** The Whisper model is loaded on application startup, which can slow down the application launch, and it's reloaded whenever settings change.

**Example:**
```python
# In main.py - initialize_tray function
loading_window.set_status(f"Loading Whisper model: {model_name}")
loading_window.set_progress(50)
app.processEvents()

try:
    tray.transcriber = WhisperTranscriber()
    loading_window.set_progress(80)
    app.processEvents()
except Exception as e:
    logger.error(f"Failed to initialize transcriber: {e}")
    QMessageBox.critical(None, "Error",
        f"Failed to load Whisper model: {str(e)}\n\nPlease check Settings to download the model.")
    loading_window.set_progress(80)
    app.processEvents()
    # Create transcriber anyway, it will handle errors during transcription
    tray.transcriber = WhisperTranscriber()

# In transcriber.py
def __init__(self):
    super().__init__()
    self.model = None
    self.worker = None
    self._cleanup_timer = QTimer()
    self._cleanup_timer.timeout.connect(self._cleanup_worker)
    self._cleanup_timer.setSingleShot(True)
    self.settings = Settings()
    self.current_language = self.settings.get('language', 'auto')
    self.load_model()  # Load model in constructor
    
def load_model(self):
    """Load the Whisper model based on current settings"""
    try:
        model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
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
        
        # Store the current model name for reference
        self.current_model_name = model_name
        
        # Load the model
        self.model = whisper.load_model(model_name)
        logger.info(f"Model '{model_name}' loaded successfully")
        
        # Update and log the current language setting
        self.current_language = self.settings.get('language', 'auto')
        lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
        logger.info(f"Current language setting: {lang_str}")
        
        # Log to console if running in terminal
        print(f"Model loaded: {model_name}, Language: {lang_str}")
        
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        print(f"Error loading model: {e}")
        raise
```

**Solution:** Implement lazy loading and model caching:

```python
# Create a model_manager.py file
class WhisperModelManager:
    """Manager for Whisper models with lazy loading and caching"""
    
    # Class-level cache of loaded models
    _model_cache = {}
    
    @staticmethod
    def get_model(model_name):
        """Get a Whisper model, loading it if necessary"""
        # Check if model is already loaded
        if model_name in WhisperModelManager._model_cache:
            logger.info(f"Using cached model: {model_name}")
            return WhisperModelManager._model_cache[model_name]
        
        # Load the model
        logger.info(f"Loading Whisper model: {model_name}")
        import whisper
        model = whisper.load_model(model_name)
        
        # Cache the model
        WhisperModelManager._model_cache[model_name] = model
        logger.info(f"Model '{model_name}' loaded and cached")
        
        return model
    
    @staticmethod
    def clear_cache():
        """Clear the model cache"""
        WhisperModelManager._model_cache.clear()
        
    @staticmethod
    def remove_from_cache(model_name):
        """Remove a specific model from the cache"""
        if model_name in WhisperModelManager._model_cache:
            del WhisperModelManager._model_cache[model_name]

# In transcriber.py
from blaze.model_manager import WhisperModelManager

class WhisperTranscriber(QObject):
    def __init__(self):
        super().__init__()
        self.model = None
        self.worker = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.settings = Settings()
        self.current_language = self.settings.get('language', 'auto')
        self.current_model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
        # Don't load model in constructor
    
    def ensure_model_loaded(self):
        """Ensure the model is loaded, loading it if necessary"""
        if self.model is None:
            self.load_model()
        return self.model
    
    def load_model(self):
        """Load the Whisper model based on current settings"""
        try:
            model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
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
            
            # Store the current model name for reference
            self.current_model_name = model_name
            
            # Load the model using the manager
            self.model = WhisperModelManager.get_model(model_name)
            logger.info(f"Model '{model_name}' loaded successfully")
            
            # Update and log the current language setting
            self.current_language = self.settings.get('language', 'auto')
            lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
            logger.info(f"Current language setting: {lang_str}")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_file(self, audio_data):
        """Transcribe audio data using a worker thread"""
        if self.worker and self.worker.isRunning():
            logger.warning("Transcription already in progress")
            return
        
        # Ensure model is loaded before transcription
        try:
            self.ensure_model_loaded()
        except Exception as e:
            self.transcription_error.emit(f"Failed to load model: {str(e)}")
            return
        
        # Rest of transcription code...