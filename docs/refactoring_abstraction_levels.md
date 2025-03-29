# Appropriate Abstraction Levels

## 4.1. Abstract Audio Processing

**Issue:** Low-level audio processing details are mixed with higher-level recording logic in `recorder.py`.

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

**Solution:** Create an abstraction layer for audio processing:

```python
# In utils/audio_utils.py
class AudioProcessor:
    """Handles audio processing operations with appropriate abstraction"""
    
    @staticmethod
    def get_device_sample_rate(audio_instance, device_info=None):
        """Get the sample rate for a device"""
        if device_info is not None:
            return int(device_info['defaultSampleRate'])
        else:
            # If no device info is available, use default input device
            return int(audio_instance.get_default_input_device_info()['defaultSampleRate'])
    
    @staticmethod
    def convert_to_whisper_format(audio_data, original_rate):
        """Convert audio data to the format expected by Whisper"""
        # Resample if needed
        if original_rate != WHISPER_SAMPLE_RATE:
            logger.info(f"Resampling audio from {original_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
            ratio = WHISPER_SAMPLE_RATE / original_rate
            output_length = int(len(audio_data) * ratio)
            audio_data = signal.resample(audio_data, output_length)
        
        # Normalize to float32 in range [-1.0, 1.0]
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        return audio_data
    
    @staticmethod
    def save_to_wav(audio_data, filename, sample_rate, channels=1, sample_width=2):
        """Save audio data to a WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
        wf.close()
        
    @staticmethod
    def frames_to_numpy(frames, dtype=np.int16):
        """Convert audio frames to numpy array"""
        return np.frombuffer(b''.join(frames), dtype=dtype)
```

Then use this in the recorder:

```python
# In recorder.py
from blaze.utils.audio_utils import AudioProcessor

def _process_recording(self):
    """Process the recording and keep it in memory"""
    try:
        logger.info("Processing recording in memory...")
        
        # Convert frames to numpy array
        audio_data = AudioProcessor.frames_to_numpy(self.frames)
        
        # Get original sample rate
        if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
            logger.warning("No sample rate information available, assuming device default")
            original_rate = AudioProcessor.get_device_sample_rate(self.audio, self.current_device_info)
        else:
            original_rate = self.current_sample_rate
        
        # Process audio using the utility class
        processed_audio = AudioProcessor.convert_to_whisper_format(audio_data, original_rate)
        
        logger.info("Recording processed in memory")
        self.recording_finished.emit(processed_audio)
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        self.recording_error.emit(f"Failed to process recording: {e}")
```

## 4.2. Abstract Model Management

**Issue:** Whisper model management details are scattered across multiple files.

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

# In transcriber.py
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

**Solution:** Create a more abstract model management interface:

```python
# In utils/whisper_model_manager.py
class WhisperModelManager:
    """High-level interface for managing Whisper models"""
    
    def __init__(self, settings_service=None):
        self.settings_service = settings_service or Settings()
        self.models_dir = self._get_models_directory()
        
    def _get_models_directory(self):
        """Get the directory where Whisper stores its models"""
        import os
        from pathlib import Path
        return os.path.join(Path.home(), ".cache", "whisper")
    
    def get_available_models(self):
        """Get list of all available models"""
        import whisper
        if hasattr(whisper, '_MODELS'):
            return list(whisper._MODELS.keys())
        return []
    
    def get_model_info(self):
        """Get comprehensive information about all models"""
        import os
        
        # Get list of available models
        available_models = self.get_available_models()
        if not available_models:
            logger.error("No available models found")
            return {}, self.models_dir
        
        # Get current active model from settings
        active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
        
        # Ensure models directory exists
        if not os.path.exists(self.models_dir):
            logger.warning(f"Whisper cache directory does not exist: {self.models_dir}")
            os.makedirs(self.models_dir, exist_ok=True)
        
        # Create model info dictionary
        model_info = {}
        for model_name in available_models:
            model_info[model_name] = self.get_single_model_info(model_name, active_model)
        
        return model_info, self.models_dir
    
    def get_single_model_info(self, model_name, active_model=None):
        """Get information about a single model"""
        import os
        
        if active_model is None:
            active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
            
        model_path = os.path.join(self.models_dir, f"{model_name}.pt")
        is_downloaded = os.path.exists(model_path)
        actual_size = 0
        
        if is_downloaded:
            actual_size = round(os.path.getsize(model_path) / (1024 * 1024))
            
        return {
            'name': model_name,
            'display_name': model_name.capitalize(),
            'is_downloaded': is_downloaded,
            'size_mb': actual_size,
            'path': model_path,
            'is_active': model_name == active_model
        }
    
    def get_model_path(self, model_name):
        """Get the file path for a specific model"""
        import os
        return os.path.join(self.models_dir, f"{model_name}.pt")
    
    def is_model_downloaded(self, model_name):
        """Check if a model is downloaded"""
        model_path = self.get_model_path(model_name)
        return os.path.exists(model_path)
    
    def load_model(self, model_name):
        """Load a Whisper model"""
        import whisper
        
        # Check if model is downloaded
        if not self.is_model_downloaded(model_name):
            error_msg = f"Model '{model_name}' is not downloaded"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Load the model
        logger.info(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name)
        logger.info(f"Model '{model_name}' loaded successfully")
        
        return model
    
    def download_model(self, model_name, progress_callback=None):
        """Download a model with progress updates"""
        import whisper
        import threading
        
        # Define a download function for the thread
        def download_thread_func():
            try:
                # Whisper's load_model will download if not present
                whisper.load_model(model_name)
                if progress_callback:
                    progress_callback(100, "Download complete")
            except Exception as e:
                logger.error(f"Error downloading model: {e}")
                if progress_callback:
                    progress_callback(-1, f"Error: {str(e)}")
        
        # Start download in a separate thread
        thread = threading.Thread(target=download_thread_func)
        thread.daemon = True
        thread.start()
        
        return thread
    
    def delete_model(self, model_name):
        """Delete a model file"""
        import os
        
        # Check if model is active
        active_model = self.settings_service.get('model', DEFAULT_WHISPER_MODEL)
        if model_name == active_model:
            raise ValueError("Cannot delete the currently active model")
            
        model_path = self.get_model_path(model_name)
        if os.path.exists(model_path):
            os.remove(model_path)
            logger.info(f"Deleted model: {model_name}")
            return True
        
        logger.warning(f"Model file not found: {model_path}")
        return False
```

Then use this in the transcriber:

```python
# In transcriber.py
from blaze.utils.whisper_model_manager import WhisperModelManager

class WhisperTranscriber(QObject):
    # ...
    
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
            raise
```

## 4.3. Abstract UI State Management

**Issue:** UI state management is mixed with UI rendering code.

**Example:**
```python
# In progress_window.py
def set_processing_mode(self):
    """Switch UI to processing mode"""
    self.processing = True
    self.volume_meter.hide()
    self.stop_button.hide()
    self.progress_bar.show()
    self.progress_bar.setValue(0)
    self.status_label.setText("Processing audio with Whisper...")
    self.setFixedHeight(220)  # Adjusted for new layout

def set_recording_mode(self):
    """Switch back to recording mode"""
    self.processing = False
    self.volume_meter.show()
    self.progress_bar.hide()
    self.stop_button.show()
    self.status_label.setText("Recording...")
    self.setFixedHeight(320)  # Adjusted for new layout
```

**Solution:** Create a state management abstraction:

```python
# In ui/state_manager.py
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
        self.window.processing = False
        self.window.volume_meter.show()
        self.window.progress_bar.hide()
        self.window.stop_button.show()
        self.window.status_label.setText("Recording...")
        self.window.setFixedHeight(320)
        
    def update(self, volume=None, **kwargs):
        if volume is not None:
            self.window.volume_meter.set_value(volume)

class ProcessingState(UIState):
    """State for processing mode"""
    def enter(self):
        self.window.processing = True
        self.window.volume_meter.hide()
        self.window.stop_button.hide()
        self.window.progress_bar.show()
        self.window.progress_bar.setValue(0)
        self.window.status_label.setText("Processing audio with Whisper...")
        self.window.setFixedHeight(220)
        
    def update(self, progress=None, status=None, **kwargs):
        if progress is not None:
            self.window.progress_bar.setValue(progress)
        if status is not None:
            self.window.status_label.setText(status)

# In progress_window.py
from blaze.ui.state_manager import RecordingState, ProcessingState

class ProgressWindow(QWidget):
    # ...
    
    def __init__(self, title="Recording"):
        # ...
        
        # Initialize states
        self.recording_state = RecordingState(self)
        self.processing_state = ProcessingState(self)
        self.current_state = None
        
        # Start in recording mode
        self.set_recording_mode()
        
    def set_processing_mode(self):
        """Switch UI to processing mode"""
        if self.current_state:
            self.current_state.exit()
        self.current_state = self.processing_state
        self.current_state.enter()
        
    def set_recording_mode(self):
        """Switch back to recording mode"""
        if self.current_state:
            self.current_state.exit()
        self.current_state = self.recording_state
        self.current_state.enter()
        
    def update_volume(self, value):
        """Update the volume meter"""
        if self.current_state:
            self.current_state.update(volume=value)
            
    def update_progress(self, percent):
        """Update the progress bar"""
        if self.current_state:
            self.current_state.update(progress=percent)
            
    def set_status(self, text):
        """Update status text"""
        if self.current_state:
            self.current_state.update(status=text)
```

This state pattern provides a cleaner separation between UI state management and the UI components themselves, making it easier to add new states or modify existing ones without changing the window class.