# Performance Optimization Opportunities

## 10.1. Inefficient Audio Processing

**Issue:** The audio processing code performs unnecessary conversions and operations, which can impact performance, especially for longer recordings.

**Example:**
```python
# In recorder.py
def _process_recording(self):
    """Process the recording and keep it in memory"""
    try:
        logger.info("Processing recording in memory...")
        # Convert frames to numpy array
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
        
        if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
            logger.warning("No sample rate information available, assuming device default")
            if self.current_device_info is not None:
                original_rate = int(self.current_device_info['defaultSampleRate'])
            else:
                # If no device info is available, we have to use a reasonable default
                # Get the default input device's sample rate
                original_rate = int(self.audio.get_default_input_device_info()['defaultSampleRate'])
        else:
            original_rate = self.current_sample_rate
            
        # Resample to 16000Hz if needed
        if original_rate != WHISPER_SAMPLE_RATE:
            logger.info(f"Resampling audio from {original_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
            # Calculate resampling ratio
            ratio = WHISPER_SAMPLE_RATE / original_rate
            output_length = int(len(audio_data) * ratio)
            
            # Resample audio
            audio_data = signal.resample(audio_data, output_length)
        else:
            logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
        
        # Normalize the audio data to float32 in the range [-1.0, 1.0] as expected by Whisper
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        logger.info("Recording processed in memory")
        self.recording_finished.emit(audio_data)
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        self.recording_error.emit(f"Failed to process recording: {e}")
```

**Solution:** Optimize audio processing with more efficient operations:

```python
# In recorder.py
def _process_recording(self):
    """Process the recording and keep it in memory"""
    try:
        logger.info("Processing recording in memory...")
        
        # Get original sample rate once at recording start
        original_rate = self._get_original_sample_rate()
        
        # Use numpy's concatenate instead of joining bytes and then converting
        # This avoids an intermediate byte string allocation
        if self.frames:
            # Convert individual frames to numpy arrays first
            frame_arrays = [np.frombuffer(frame, dtype=np.int16) for frame in self.frames]
            # Then concatenate them efficiently
            audio_data = np.concatenate(frame_arrays)
        else:
            audio_data = np.array([], dtype=np.int16)
            
        # Resample to 16000Hz if needed
        if original_rate != WHISPER_SAMPLE_RATE:
            logger.info(f"Resampling audio from {original_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
            
            # Use more efficient resampling if available
            try:
                # Try to use librosa's resampling which can be faster
                import librosa
                audio_data = librosa.resample(
                    audio_data.astype(np.float32) / 32768.0,  # Convert to float32 first
                    orig_sr=original_rate,
                    target_sr=WHISPER_SAMPLE_RATE
                )
                # librosa returns already normalized data
                normalized = True
            except ImportError:
                # Fall back to scipy's resampling
                ratio = WHISPER_SAMPLE_RATE / original_rate
                output_length = int(len(audio_data) * ratio)
                audio_data = signal.resample(audio_data, output_length)
                normalized = False
        else:
            logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
            normalized = False
        
        # Normalize if not already done
        if not normalized:
            # Normalize the audio data to float32 in the range [-1.0, 1.0] as expected by Whisper
            audio_data = audio_data.astype(np.float32) / 32768.0
        
        logger.info("Recording processed in memory")
        self.recording_finished.emit(audio_data)
        
        # Clear frames to free memory
        self.frames = []
        
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        self.recording_error.emit(f"Failed to process recording: {e}")
        
def _get_original_sample_rate(self):
    """Get the original sample rate, with caching"""
    if hasattr(self, 'current_sample_rate') and self.current_sample_rate is not None:
        return self.current_sample_rate
        
    logger.warning("No sample rate information available, assuming device default")
    if self.current_device_info is not None:
        return int(self.current_device_info['defaultSampleRate'])
    else:
        # If no device info is available, we have to use a reasonable default
        # Get the default input device's sample rate
        return int(self.audio.get_default_input_device_info()['defaultSampleRate'])
```

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
```

## 10.3. Inefficient UI Updates

**Issue:** The application performs frequent UI updates during recording and transcription, which can impact performance.

**Example:**
```python
# In recorder.py - _callback method
def _callback(self, in_data, frame_count, time_info, status):
    if status:
        logger.warning(f"Recording status: {status}")
    try:
        if self.is_recording:
            self.frames.append(in_data)
            # Calculate and emit volume level
            try:
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                if len(audio_data) > 0:
                    # Calculate RMS with protection against zero/negative values
                    squared = np.abs(audio_data)**2
                    mean_squared = np.mean(squared) if np.any(squared) else 0
                    rms = np.sqrt(mean_squared) if mean_squared > 0 else 0
                    # Normalize to 0-1 range
                    volume = min(1.0, max(0.0, rms / 32768.0))
                else:
                    volume = 0.0
                self.volume_updated.emit(volume)
            except Exception as e:
                logger.warning(f"Error calculating volume: {e}")
                self.volume_updated.emit(0.0)
            return (in_data, pyaudio.paContinue)
    except RuntimeError:
        # Handle case where object is being deleted
        logger.warning("AudioRecorder object is being cleaned up")
        return (in_data, pyaudio.paComplete)
    return (in_data, pyaudio.paComplete)

# In main.py - update_volume_meter method
def update_volume_meter(self, value):
    # Update debug window first
    if hasattr(self, 'debug_window'):
        self.debug_window.update_values(value)
        
    # Then update volume meter as before
    if self.progress_window and self.recording:
        self.progress_window.update_volume(value)
```

**Solution:** Throttle UI updates to reduce CPU usage:

```python
# In recorder.py
class AudioRecorder(QObject):
    def __init__(self):
        super().__init__()
        # ...
        
        # Add throttling for volume updates
        self.last_volume_update_time = 0
        self.volume_update_interval = 50  # ms
        
    def _callback(self, in_data, frame_count, time_info, status):
        if status:
            logger.warning(f"Recording status: {status}")
        try:
            if self.is_recording:
                self.frames.append(in_data)
                
                # Throttle volume updates
                current_time = time.time() * 1000  # Convert to ms
                if current_time - self.last_volume_update_time >= self.volume_update_interval:
                    self._update_volume(in_data)
                    self.last_volume_update_time = current_time
                    
                return (in_data, pyaudio.paContinue)
        except RuntimeError:
            # Handle case where object is being deleted
            logger.warning("AudioRecorder object is being cleaned up")
            return (in_data, pyaudio.paComplete)
        return (in_data, pyaudio.paComplete)
    
    def _update_volume(self, in_data):
        """Calculate and emit volume level"""
        try:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            if len(audio_data) > 0:
                # Use more efficient calculation
                # Take absolute values and calculate mean
                mean_abs = np.mean(np.abs(audio_data))
                # Normalize to 0-1 range
                volume = min(1.0, max(0.0, mean_abs / 32768.0))
            else:
                volume = 0.0
            self.volume_updated.emit(volume)
        except Exception as e:
            logger.warning(f"Error calculating volume: {e}")
            self.volume_updated.emit(0.0)
```

## 10.4. Inefficient Settings Access

**Issue:** The application frequently accesses settings, which can involve disk I/O and slow down operations.

**Example:**
```python
# In various places
settings = Settings()
model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
language_code = settings.get('language', 'auto')

# In update_tooltip method
def update_tooltip(self, recognized_text=None):
    """Update the tooltip with app name, version, model and language information"""
    import sys
    
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    language_code = settings.get('language', 'auto')
    
    # ...
```

**Solution:** Implement settings caching and batch updates:

```python
# In settings.py
class Settings:
    # Class-level cache
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the settings object"""
        self.settings = QSettings(APP_NAME, APP_NAME)
        self._load_cache()
        
    def _load_cache(self):
        """Load all settings into cache"""
        # Load common settings into cache
        common_keys = ['model', 'language', 'mic_index', 'sample_rate_mode']
        for key in common_keys:
            default = self._get_default(key)
            value = self.settings.value(key, default)
            # Validate and store in cache
            Settings._cache[key] = self._validate(key, value, default)
    
    def _get_default(self, key):
        """Get default value for a key"""
        if key == 'model':
            return DEFAULT_WHISPER_MODEL
        elif key == 'language':
            return 'auto'
        elif key == 'sample_rate_mode':
            return DEFAULT_SAMPLE_RATE_MODE
        return None
    
    def _validate(self, key, value, default):
        """Validate a setting value"""
        # Existing validation logic...
        return value
    
    def get(self, key, default=None):
        """Get a setting value, using cache when possible"""
        # Check cache first
        if key in Settings._cache:
            return Settings._cache[key]
        
        # Not in cache, get from QSettings
        value = self.settings.value(key, default)
        
        # Validate and cache the value
        validated_value = self._validate(key, value, default)
        Settings._cache[key] = validated_value
        
        return validated_value
    
    def set(self, key, value):
        """Set a setting value and update cache"""
        # Validate before saving
        validated_value = self._validate(key, value, self._get_default(key))
        
        # Update QSettings
        self.settings.setValue(key, validated_value)
        
        # Update cache
        Settings._cache[key] = validated_value
        
        # Sync to disk
        self.settings.sync()
        
    def clear_cache(self):
        """Clear the settings cache"""
        Settings._cache.clear()
        self._load_cache()
```

## 10.5. Inefficient File Operations

**Issue:** The application performs inefficient file operations, particularly when checking for model files.

**Example:**
```python
# In whisper_model_manager.py
def get_model_info():
    """Get comprehensive information about all Whisper models"""
    import whisper
    import os
    from pathlib import Path
    
    # Get the directory where Whisper stores its models
    models_dir = os.path.join(Path.home(), ".cache", "whisper")
    
    # Get list of available models from Whisper
    available_models = []
    if hasattr(whisper, '_MODELS'):
        available_models = list(whisper._MODELS.keys())
        logger.info(f"Available models in whisper._MODELS: {available_models}")
    else:
        logger.error("whisper._MODELS not found")
        return {}, models_dir
    
    # Get current active model from settings
    settings = Settings()
    active_model = settings.get('model', DEFAULT_WHISPER_MODEL)
    
    # Scan the directory for all model files
    if os.path.exists(models_dir):
        logger.info(f"Files in whisper cache: {os.listdir(models_dir)}")
    else:
        logger.warning(f"Whisper cache directory does not exist: {models_dir}")
        os.makedirs(models_dir, exist_ok=True)
    
    # Create model info dictionary
    model_info = {}
    for model_name in available_models:
        # Check for exact match only (model_name.pt)
        model_path = os.path.join(models_dir, f"{model_name}.pt")
        is_downloaded = os.path.exists(model_path)
        actual_size = 0
        
        # If model file exists, get its size
        if is_downloaded:
            actual_size = round(os.path.getsize(model_path) / (1024 * 1024))  # Convert to MB and round to integer
            logger.info(f"Found model {model_name} at {model_path}")
        
        # Create model info object
        model_info[model_name] = {
            'name': model_name,
            'display_name': model_name.capitalize(),
            'is_downloaded': is_downloaded,
            'size_mb': actual_size,
            'path': model_path,
            'is_active': model_name == active_model
        }
    
    return model_info, models_dir
```

**Solution:** Optimize file operations with caching and batch processing:

```python
# In whisper_model_manager.py
class ModelInfoCache:
    """Cache for model information to reduce file system operations"""
    _cache = {}
    _cache_time = 0
    _cache_lifetime = 60  # seconds
    
    @staticmethod
    def get_model_info():
        """Get model information, using cache when possible"""
        current_time = time.time()
        
        # Check if cache is valid
        if (ModelInfoCache._cache and 
            current_time - ModelInfoCache._cache_time < ModelInfoCache._cache_lifetime):
            return ModelInfoCache._cache.copy(), ModelInfoCache._cache.get('_models_dir', '')
        
        # Cache is invalid or empty, refresh it
        model_info, models_dir = ModelInfoCache._fetch_model_info()
        
        # Update cache
        ModelInfoCache._cache = model_info.copy()
        ModelInfoCache._cache['_models_dir'] = models_dir
        ModelInfoCache._cache_time = current_time
        
        return model_info, models_dir
    
    @staticmethod
    def invalidate_cache():
        """Invalidate the cache"""
        ModelInfoCache._cache = {}
        ModelInfoCache._cache_time = 0
    
    @staticmethod
    def _fetch_model_info():
        """Fetch model information from the file system"""
        import whisper
        import os
        from pathlib import Path
        
        # Get the directory where Whisper stores its models
        models_dir = os.path.join(Path.home(), ".cache", "whisper")
        
        # Get list of available models from Whisper
        available_models = []
        if hasattr(whisper, '_MODELS'):
            available_models = list(whisper._MODELS.keys())
            logger.info(f"Available models in whisper._MODELS: {available_models}")
        else:
            logger.error("whisper._MODELS not found")
            return {}, models_dir
        
        # Get current active model from settings
        settings = Settings()
        active_model = settings.get('model', DEFAULT_WHISPER_MODEL)
        
        # Check if models directory exists
        if not os.path.exists(models_dir):
            logger.warning(f"Whisper cache directory does not exist: {models_dir}")
            os.makedirs(models_dir, exist_ok=True)
            return {model_name: {
                'name': model_name,
                'display_name': model_name.capitalize(),
                'is_downloaded': False,
                'size_mb': 0,
                'path': os.path.join(models_dir, f"{model_name}.pt"),
                'is_active': model_name == active_model
            } for model_name in available_models}, models_dir
        
        # Get all files in the directory at once
        try:
            dir_files = set(os.listdir(models_dir))
        except Exception as e:
            logger.error(f"Error listing models directory: {e}")
            dir_files = set()
        
        # Create model info dictionary
        model_info = {}
        for model_name in available_models:
            # Check if model file exists
            model_filename = f"{model_name}.pt"
            is_downloaded = model_filename in dir_files
            
            # Get model path
            model_path = os.path.join(models_dir, model_filename)
            
            # Get file size if downloaded
            actual_size = 0
            if is_downloaded:
                try:
                    actual_size = round(os.path.getsize(model_path) / (1024 * 1024))
                except Exception as e:
                    logger.error(f"Error getting size of model file {model_path}: {e}")
            
            # Create model info object
            model_info[model_name] = {
                'name': model_name,
                'display_name': model_name.capitalize(),
                'is_downloaded': is_downloaded,
                'size_mb': actual_size,
                'path': model_path,
                'is_active': model_name == active_model
            }
        
        return model_info, models_dir

# Replace get_model_info function with cache access
def get_model_info():
    """Get comprehensive information about all Whisper models"""
    return ModelInfoCache.get_model_info()
```

These optimizations can significantly improve the application's performance, especially for operations that are performed frequently or involve heavy processing.