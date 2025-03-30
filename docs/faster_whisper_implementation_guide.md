# Faster Whisper Implementation Guide

## Introduction

This guide provides detailed implementation instructions for transitioning Syllablaze to Faster Whisper. It includes code examples and specific changes required for each component.

## Prerequisites

Before beginning the implementation, ensure the following dependencies are installed:

```bash
pip install faster-whisper>=1.1.0
```

For GPU support, ensure the following NVIDIA libraries are installed:
- cuBLAS for CUDA 12
- cuDNN 9 for CUDA 12

## Core Implementation Changes

### 1. Update WhisperModelManager

First, update the `WhisperModelManager` class to use Faster Whisper:

```python
class WhisperModelManager:
    """High-level interface for managing Whisper models"""
    
    def __init__(self, settings_service=None):
        self.settings_service = settings_service or Settings()
        self.models_dir = self._get_models_directory()
        
    def _get_models_directory(self):
        """Get the directory where Whisper stores its models"""
        import os
        from pathlib import Path
        
        # Faster Whisper uses the same directory structure as original Whisper
        return os.path.join(Path.home(), ".cache", "whisper")
    
    def load_model(self, model_name):
        """Load a Whisper model"""
        compute_type = self.settings_service.get('compute_type', 'float32')
        device = self.settings_service.get('device', 'cpu')
        
        from faster_whisper import WhisperModel
        
        # Map compute types to Faster Whisper format
        compute_type_map = {
            'float32': 'float32',
            'float16': 'float16',
            'int8': 'int8'
        }
        
        # For GPU with mixed precision
        if device == 'cuda' and compute_type == 'float16':
            ct = 'float16'
        # For GPU with int8 quantization
        elif device == 'cuda' and compute_type == 'int8':
            ct = 'int8_float16'
        # For CPU
        else:
            ct = compute_type_map.get(compute_type, 'float32')
        
        logger.info(f"Loading Faster Whisper model: {model_name} (device: {device}, compute_type: {ct})")
        model = WhisperModel(model_name, device=device, compute_type=ct)
        logger.info(f"Model '{model_name}' loaded successfully")
        
        return model
```

### 2. Create FasterWhisperTranscriber

Create a new transcriber class that uses Faster Whisper:

```python
class FasterWhisperTranscriber(QObject):
    transcription_progress = pyqtSignal(str)
    transcription_progress_percent = pyqtSignal(int)
    transcription_finished = pyqtSignal(str)
    transcription_error = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    
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
            logger.error(f"Failed to load Faster Whisper model: {e}")
            print(f"Error loading model: {e}")
            self.transcription_error.emit(f"Failed to load Faster Whisper model: {e}")
            raise
    
    def transcribe(self, audio_data):
        """Transcribe audio data directly from memory"""
        try:
            # Prepare for transcription
            _, _, lang_str = self._prepare_for_transcription()
            
            # Emit progress update
            self.transcription_progress.emit("Processing audio...")
            
            print(f"Transcribing with model: {self.current_model_name}, language: {lang_str}")
            
            # Get transcription options from settings
            beam_size = self.settings.get('beam_size', 5)
            vad_filter = self.settings.get('vad_filter', True)
            word_timestamps = self.settings.get('word_timestamps', False)
            
            # Run transcription with Faster Whisper
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=beam_size,
                language=None if self.current_language == 'auto' else self.current_language,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps
            )
            
            # Convert generator to list to complete transcription
            segments_list = list(segments)
            
            # Combine all segment texts
            text = " ".join([segment.text for segment in segments_list])
            
            if not text:
                raise ValueError("No text was transcribed")
                
            self.transcription_progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: [{text}]")
            self.transcription_finished.emit(text)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.transcription_error.emit(str(e))
```

### 3. Create FasterWhisperTranscriptionWorker

Create a worker class for asynchronous transcription:

```python
class FasterWhisperTranscriptionWorker(QThread):
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
            
            self.progress.emit("Processing audio with Faster Whisper...")
            self.progress_percent.emit(30)
            
            # Get transcription options from settings
            beam_size = self.settings.get('beam_size', 5)
            vad_filter = self.settings.get('vad_filter', True)
            word_timestamps = self.settings.get('word_timestamps', False)
            
            # Log the language being used for transcription
            lang_str = "auto-detect" if self.language == 'auto' else self.language
            logger.info(f"Transcribing with language: {lang_str}")
            
            # Run transcription with Faster Whisper
            segments, info = self.model.transcribe(
                self.audio_data,
                beam_size=beam_size,
                language=None if self.language == 'auto' else self.language,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps
            )
            
            # Convert generator to list to complete transcription
            segments_list = list(segments)
            
            # Combine all segment texts
            text = " ".join([segment.text for segment in segments_list])
            
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
```

### 4. Update Settings

Add new settings for Faster Whisper:

```python
# In settings.py or constants.py

# Default settings
DEFAULT_COMPUTE_TYPE = 'float32'  # or 'float16', 'int8'
DEFAULT_DEVICE = 'cpu'  # or 'cuda'
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True
DEFAULT_WORD_TIMESTAMPS = False

# Add these to the settings initialization
def init_default_settings(self):
    # Existing settings...
    
    # Faster Whisper settings
    self.settings.setdefault('compute_type', DEFAULT_COMPUTE_TYPE)
    self.settings.setdefault('device', DEFAULT_DEVICE)
    self.settings.setdefault('beam_size', DEFAULT_BEAM_SIZE)
    self.settings.setdefault('vad_filter', DEFAULT_VAD_FILTER)
    self.settings.setdefault('word_timestamps', DEFAULT_WORD_TIMESTAMPS)
```

### 5. Update Settings UI

Add new options to the settings window:

```python
# In settings_window.py

# Add these widgets to the settings window
self.compute_type_combo = QComboBox()
self.compute_type_combo.addItems(['float32', 'float16', 'int8'])
self.compute_type_combo.setCurrentText(self.settings.get('compute_type', DEFAULT_COMPUTE_TYPE))
self.compute_type_combo.currentTextChanged.connect(self.on_compute_type_changed)

self.device_combo = QComboBox()
self.device_combo.addItems(['cpu', 'cuda'])
self.device_combo.setCurrentText(self.settings.get('device', DEFAULT_DEVICE))
self.device_combo.currentTextChanged.connect(self.on_device_changed)

self.beam_size_spin = QSpinBox()
self.beam_size_spin.setRange(1, 10)
self.beam_size_spin.setValue(self.settings.get('beam_size', DEFAULT_BEAM_SIZE))
self.beam_size_spin.valueChanged.connect(self.on_beam_size_changed)

self.vad_filter_check = QCheckBox("Use VAD filter")
self.vad_filter_check.setChecked(self.settings.get('vad_filter', DEFAULT_VAD_FILTER))
self.vad_filter_check.stateChanged.connect(self.on_vad_filter_changed)

self.word_timestamps_check = QCheckBox("Generate word timestamps")
self.word_timestamps_check.setChecked(self.settings.get('word_timestamps', DEFAULT_WORD_TIMESTAMPS))
self.word_timestamps_check.stateChanged.connect(self.on_word_timestamps_changed)

# Add corresponding event handlers
def on_compute_type_changed(self, value):
    self.settings.set('compute_type', value)
    
def on_device_changed(self, value):
    self.settings.set('device', value)
    
def on_beam_size_changed(self, value):
    self.settings.set('beam_size', value)
    
def on_vad_filter_changed(self, state):
    self.settings.set('vad_filter', state == Qt.CheckState.Checked)
    
def on_word_timestamps_changed(self, state):
    self.settings.set('word_timestamps', state == Qt.CheckState.Checked)
```

## Integration Strategy

### 1. Update requirements.txt

```
# Existing requirements
PyQt6>=6.0.0
numpy>=1.20.0
scipy>=1.7.0
pyaudio>=0.2.11
keyboard
psutil

# Add Faster Whisper
faster-whisper>=1.1.0
```

### 2. Update setup.py

```python
# In setup.py

install_requires=[
    # Existing requirements
    'PyQt6>=6.0.0',
    'numpy>=1.20.0',
    'scipy>=1.7.0',
    'pyaudio>=0.2.11',
    'keyboard',
    'psutil',
    
    # Add Faster Whisper
    'faster-whisper>=1.1.0',
],
```

## Testing Strategy

1. **Unit Tests**:
   - Test model loading with different settings
   - Test transcription with various audio inputs
   - Test settings persistence

2. **Integration Tests**:
   - Test end-to-end transcription flow
   - Test UI interaction with new settings

3. **Performance Tests**:
   - Benchmark transcription speed
   - Measure memory usage

## Deployment Considerations

1. **Documentation**:
   - Update user documentation with new settings
   - Provide performance tuning guidelines

2. **Error Handling**:
   - Add specific error messages for Faster Whisper issues

## Conclusion

This implementation guide provides a detailed roadmap for implementing Faster Whisper in Syllablaze. By following these steps, you can achieve significant performance improvements while maintaining a clean, maintainable codebase.