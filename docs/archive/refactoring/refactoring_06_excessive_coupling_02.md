## 5.2. Tight Coupling to Whisper Implementation

**Issue:** The code is tightly coupled to the specific Whisper implementation details.

**Example:**
```python
# In transcriber.py
def transcribe(self, audio_data):
    """Transcribe audio data directly from memory"""
    try:
        # ...
        
        # Run transcription with language setting
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=None if self.current_language == 'auto' else self.current_language
        )
        
        text = result["text"].strip()
        # ...
    except Exception as e:
        # ...

# In settings.py
class Settings:
    # Get valid models from whisper._MODELS
    VALID_MODELS = list(whisper._MODELS.keys()) if hasattr(whisper, '_MODELS') else []
```

**Solution:** Create an abstraction layer for transcription:

```python
# In core/transcription.py
class TranscriptionEngine:
    """Abstract base class for transcription engines"""
    
    def __init__(self):
        pass
        
    def load_model(self, model_name):
        """Load a model by name"""
        raise NotImplementedError
        
    def transcribe(self, audio_data, language=None):
        """Transcribe audio data to text"""
        raise NotImplementedError
        
    def get_available_models(self):
        """Get list of available models"""
        raise NotImplementedError
        
    def get_available_languages(self):
        """Get list of available languages"""
        raise NotImplementedError

class WhisperTranscriptionEngine(TranscriptionEngine):
    """Whisper implementation of the transcription engine"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.model_name = None
        
    def load_model(self, model_name):
        import whisper
        self.model = whisper.load_model(model_name)
        self.model_name = model_name
        return self.model
        
    def transcribe(self, audio_data, language=None):
        if self.model is None:
            raise ValueError("Model not loaded")
            
        result = self.model.transcribe(
            audio_data,
            fp16=False,
            language=language
        )
        
        return result["text"].strip()
        
    def get_available_models(self):
        import whisper
        if hasattr(whisper, '_MODELS'):
            return list(whisper._MODELS.keys())
        return []
        
    def get_available_languages(self):
        # Return Whisper's supported languages
        from blaze.constants import VALID_LANGUAGES
        return VALID_LANGUAGES
```

Then use this abstraction in the application:

```python
# In transcriber.py
from blaze.core.transcription import WhisperTranscriptionEngine

class WhisperTranscriber(QObject):
    # ...
    
    def __init__(self):
        super().__init__()
        self.engine = WhisperTranscriptionEngine()
        self.worker = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.settings = Settings()
        self.current_language = self.settings.get('language', 'auto')
        self.load_model()
        
    def load_model(self):
        """Load the Whisper model based on current settings"""
        try:
            model_name = self.settings.get('model', DEFAULT_WHISPER_MODEL)
            logger.info(f"Loading Whisper model: {model_name}")
            
            # Store the current model name for reference
            self.current_model_name = model_name
            
            # Load the model using the engine
            self.engine.load_model(model_name)
            
            # Update and log the current language setting
            self.current_language = self.settings.get('language', 'auto')
            lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
            logger.info(f"Current language setting: {lang_str}")
                
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
            
    def transcribe(self, audio_data):
        """Transcribe audio data directly from memory"""
        try:
            # Prepare for transcription
            self.reload_model_if_needed()
            
            # Emit progress update
            self.transcription_progress.emit("Processing audio...")
            
            # Get language parameter
            language = None if self.current_language == 'auto' else self.current_language
            
            # Use the engine to transcribe
            text = self.engine.transcribe(audio_data, language)
            
            if not text:
                raise ValueError("No text was transcribed")
                
            self.transcription_progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: [{text}]")
            self.transcription_finished.emit(text)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.transcription_error.emit(str(e))