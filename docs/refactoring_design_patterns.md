# Potential for Design Patterns Implementation

## 8.1. Observer Pattern Enhancement

**Issue:** The application already uses the Observer pattern through Qt's signal/slot mechanism, but it's not consistently applied across all components.

**Example:**
```python
# In main.py
def update_tooltip(self, recognized_text=None):
    """Update the tooltip with app name, version, model and language information"""
    import sys
    
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    language_code = settings.get('language', 'auto')
    
    # Get language display name from VALID_LANGUAGES if available
    if language_code in VALID_LANGUAGES:
        language_display = f"Language: {VALID_LANGUAGES[language_code]}"
    else:
        language_display = "Language: auto-detect" if language_code == 'auto' else f"Language: {language_code}"
    
    tooltip = f"{APP_NAME} {APP_VERSION}\nModel: {model_name}\n{language_display}"
    
    # Add recognized text to tooltip if provided
    if recognized_text:
        # Truncate text if it's too long
        max_length = 100
        if len(recognized_text) > max_length:
            recognized_text = recognized_text[:max_length] + "..."
        tooltip += f"\nRecognized: {recognized_text}"
    
    # Print tooltip info to console with flush
    print(f"TOOLTIP UPDATE: MODEL={model_name}, {language_display}", flush=True)
    sys.stdout.flush()
        
    self.setToolTip(tooltip)

# In settings_window.py
def on_model_activated(self, model_name):
    """Handle model activation from the table"""
    if hasattr(self, 'current_model') and model_name == self.current_model:
        logger.info(f"Model {model_name} is already active, no change needed")
        print(f"Model {model_name} is already active, no change needed")
        return
        
    try:
        # Set the model
        self.settings.set('model', model_name)
        self.current_model = model_name
        
        # No modal dialog needed
        
        # Update any active transcriber instances
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'transcriber') and widget.transcriber:
                widget.transcriber.update_model(model_name)
        
        # Import and use the update_tray_tooltip function
        from blaze.main import update_tray_tooltip
        update_tray_tooltip()
        
        # Log confirmation that the change was successful
        logger.info(f"Model successfully changed to: {model_name}")
        print(f"Model successfully changed to: {model_name}")
                
        self.initialization_complete.emit()
    except ValueError as e:
        logger.error(f"Failed to set model: {e}")
        QMessageBox.warning(self, "Error", str(e))
```

**Solution:** Implement a more consistent Observer pattern using a central event bus:

```python
# Create an events.py file
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """Central event bus for application-wide events"""
    # Settings events
    settings_changed = pyqtSignal(str, object)  # key, value
    model_activated = pyqtSignal(str)           # model_name
    language_changed = pyqtSignal(str)          # language_code
    
    # Recording events
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_completed = pyqtSignal(object)    # audio_data
    
    # Transcription events
    transcription_started = pyqtSignal()
    transcription_completed = pyqtSignal(str)   # transcribed_text
    
    # UI update events
    tooltip_update_needed = pyqtSignal(dict)    # tooltip_info
    
    # Singleton instance
    _instance = None
    
    @staticmethod
    def instance():
        if EventBus._instance is None:
            EventBus._instance = EventBus()
        return EventBus._instance

# In main.py
from blaze.events import EventBus

def __init__(self):
    super().__init__()
    # ...
    
    # Connect to event bus
    self._connect_to_event_bus()
    
def _connect_to_event_bus(self):
    event_bus = EventBus.instance()
    event_bus.model_activated.connect(self._on_model_changed)
    event_bus.language_changed.connect(self._on_language_changed)
    event_bus.tooltip_update_needed.connect(self._update_tooltip_from_info)
    event_bus.transcription_completed.connect(self._on_transcription_completed)
    
def _on_model_changed(self, model_name):
    self._update_tooltip()
    
def _on_language_changed(self, language_code):
    self._update_tooltip()
    
def _on_transcription_completed(self, text):
    self._update_tooltip(recognized_text=text)
    
def _update_tooltip(self, recognized_text=None):
    """Update the tooltip with app name, version, model and language information"""
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    language_code = settings.get('language', 'auto')
    
    # Get language display name from VALID_LANGUAGES if available
    if language_code in VALID_LANGUAGES:
        language_display = f"Language: {VALID_LANGUAGES[language_code]}"
    else:
        language_display = "Language: auto-detect" if language_code == 'auto' else f"Language: {language_code}"
    
    tooltip_info = {
        'app_name': APP_NAME,
        'app_version': APP_VERSION,
        'model_name': model_name,
        'language_display': language_display,
        'recognized_text': recognized_text
    }
    
    # Emit event for tooltip update
    EventBus.instance().tooltip_update_needed.emit(tooltip_info)
    
def _update_tooltip_from_info(self, info):
    """Update tooltip from provided info dictionary"""
    tooltip = f"{info['app_name']} {info['app_version']}\nModel: {info['model_name']}\n{info['language_display']}"
    
    # Add recognized text to tooltip if provided
    if info.get('recognized_text'):
        # Truncate text if it's too long
        recognized_text = info['recognized_text']
        max_length = 100
        if len(recognized_text) > max_length:
            recognized_text = recognized_text[:max_length] + "..."
        tooltip += f"\nRecognized: {recognized_text}"
    
    # Set the tooltip
    self.setToolTip(tooltip)

# In settings_window.py
from blaze.events import EventBus

def on_model_activated(self, model_name):
    """Handle model activation from the table"""
    if hasattr(self, 'current_model') and model_name == self.current_model:
        logger.info(f"Model {model_name} is already active, no change needed")
        return
        
    try:
        # Set the model
        self.settings.set('model', model_name)
        self.current_model = model_name
        
        # Emit event for model activation
        EventBus.instance().model_activated.emit(model_name)
        
        # Log confirmation that the change was successful
        logger.info(f"Model successfully changed to: {model_name}")
                
        self.initialization_complete.emit()
    except ValueError as e:
        logger.error(f"Failed to set model: {e}")
        QMessageBox.warning(self, "Error", str(e))
```

## 8.2. Factory Method Pattern for UI Components

**Issue:** UI components are created directly in multiple places, making it difficult to maintain consistent styling and behavior.

**Example:**
```python
# In main.py
def toggle_recording(self):
    # ...
    # Show progress window
    if not self.progress_window:
        self.progress_window = ProgressWindow("Voice Recording")
        self.progress_window.stop_clicked.connect(self.stop_recording)
    self.progress_window.show()
    # ...

def toggle_settings(self):
    if not self.settings_window:
        self.settings_window = SettingsWindow()
    # ...

# In initialize_tray function
loading_window = LoadingWindow()
loading_window.show()
```

**Solution:** Implement a Factory Method pattern for UI components:

```python
# Create a ui_factory.py file
class UIFactory:
    """Factory for creating UI components with consistent styling and behavior"""
    
    @staticmethod
    def create_progress_window(title="Voice Recording"):
        """Create a progress window with standard configuration"""
        from blaze.ui.progress_window import ProgressWindow
        window = ProgressWindow(title)
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def create_settings_window():
        """Create a settings window with standard configuration"""
        from blaze.ui.settings_window import SettingsWindow
        window = SettingsWindow()
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def create_loading_window():
        """Create a loading window with standard configuration"""
        from blaze.ui.loading_window import LoadingWindow
        window = LoadingWindow()
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def create_processing_window():
        """Create a processing window with standard configuration"""
        from blaze.ui.processing_window import ProcessingWindow
        window = ProcessingWindow()
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def _apply_common_window_config(window):
        """Apply common configuration to all windows"""
        # Center the window
        from blaze.utils import center_window
        center_window(window)
        
        # Apply common styling
        window.setWindowIcon(QIcon.fromTheme("syllablaze"))
        
        # Apply any other common configuration
        # ...

# In main.py
from blaze.ui.ui_factory import UIFactory

def toggle_recording(self):
    # ...
    # Show progress window
    if not self.progress_window:
        self.progress_window = UIFactory.create_progress_window("Voice Recording")
        self.progress_window.stop_clicked.connect(self.stop_recording)
    self.progress_window.show()
    # ...

def toggle_settings(self):
    if not self.settings_window:
        self.settings_window = UIFactory.create_settings_window()
    # ...

# In initialize_tray function
loading_window = UIFactory.create_loading_window()
loading_window.show()
```

## 8.3. State Pattern for Recording States

**Issue:** The application manages recording states using boolean flags and conditional logic, making it difficult to understand and maintain the state transitions.

**Example:**
```python
# In main.py
def toggle_recording(self):
    if self.recording:
        # Stop recording
        self.recording = False
        self.record_action.setText("Start Recording")
        self.setIcon(self.normal_icon)
        
        # Update progress window before stopping recording
        if self.progress_window:
            self.progress_window.set_processing_mode()
            self.progress_window.set_status("Processing audio...")
        
        # Stop the actual recording
        if self.recorder:
            try:
                self.recorder.stop_recording()
            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                if self.progress_window:
                    self.progress_window.close()
                    self.progress_window = None
                return
    else:
        # Start recording
        self.recording = True
        # Show progress window
        if not self.progress_window:
            self.progress_window = ProgressWindow("Voice Recording")
            self.progress_window.stop_clicked.connect(self.stop_recording)
        self.progress_window.show()
        
        # Start recording
        self.record_action.setText("Stop Recording")
        self.setIcon(self.recording_icon)
        self.recorder.start_recording()
```

**Solution:** Implement the State pattern for recording states:

```python
# Create a states.py file
class RecordingState:
    """Base class for recording states"""
    def __init__(self, context):
        self.context = context
    
    def toggle_recording(self):
        """Toggle recording state"""
        pass
    
    def update_ui(self):
        """Update UI for this state"""
        pass
    
    def handle_error(self, error):
        """Handle errors in this state"""
        pass

class IdleState(RecordingState):
    """State when not recording"""
    def toggle_recording(self):
        # Start recording
        try:
            # Update UI first
            self.context.record_action.setText("Stop Recording")
            self.context.setIcon(self.context.recording_icon)
            
            # Show progress window
            if not self.context.progress_window:
                self.context.progress_window = UIFactory.create_progress_window("Voice Recording")
                self.context.progress_window.stop_clicked.connect(self.context.stop_recording)
            self.context.progress_window.show()
            
            # Start actual recording
            self.context.recorder.start_recording()
            
            # Change state
            self.context.set_state(RecordingState(self.context))
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.handle_error(str(e))
    
    def update_ui(self):
        self.context.record_action.setText("Start Recording")
        self.context.setIcon(self.context.normal_icon)
    
    def handle_error(self, error):
        QMessageBox.critical(None, "Recording Error", error)

class RecordingState(RecordingState):
    """State when actively recording"""
    def toggle_recording(self):
        # Stop recording
        try:
            # Update UI first
            self.context.record_action.setText("Start Recording")
            self.context.setIcon(self.context.normal_icon)
            
            # Update progress window
            if self.context.progress_window:
                self.context.progress_window.set_processing_mode()
                self.context.progress_window.set_status("Processing audio...")
            
            # Stop actual recording
            self.context.recorder.stop_recording()
            
            # Change state
            self.context.set_state(ProcessingState(self.context))
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.handle_error(str(e))
    
    def update_ui(self):
        self.context.record_action.setText("Stop Recording")
        self.context.setIcon(self.context.recording_icon)
    
    def handle_error(self, error):
        if self.context.progress_window:
            self.context.progress_window.close()
            self.context.progress_window = None
        
        QMessageBox.critical(None, "Recording Error", error)
        
        # Change state back to idle
        self.context.set_state(IdleState(self.context))

class ProcessingState(RecordingState):
    """State when processing recorded audio"""
    def toggle_recording(self):
        # Cannot toggle while processing
        pass
    
    def update_ui(self):
        self.context.record_action.setText("Processing...")
        self.context.record_action.setEnabled(False)
    
    def handle_transcription_finished(self, text):
        # Re-enable recording action
        self.context.record_action.setEnabled(True)
        
        # Close progress window
        if self.context.progress_window:
            self.context.progress_window.close()
            self.context.progress_window = None
        
        # Change state back to idle
        self.context.set_state(IdleState(self.context))

# In main.py
from blaze.states import IdleState, RecordingState, ProcessingState

class TrayRecorder(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        # ...
        
        # Initialize state
        self.state = None
        
    def initialize(self):
        # ...
        
        # Set initial state
        self.set_state(IdleState(self))
    
    def set_state(self, state):
        """Change the current state"""
        self.state = state
        self.state.update_ui()
    
    def toggle_recording(self):
        """Toggle recording based on current state"""
        if self.state:
            self.state.toggle_recording()
    
    def handle_transcription_finished(self, text):
        """Handle transcription completion"""
        # Copy text to clipboard
        QApplication.clipboard().setText(text)
        
        # Show notification
        self.show_transcription_notification(text)
        
        # Update state
        if isinstance(self.state, ProcessingState):
            self.state.handle_transcription_finished(text)
```

## 8.4. Strategy Pattern for Audio Processing

**Issue:** The audio processing logic is tightly coupled to the recorder class, making it difficult to change or extend.

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

**Solution:** Implement the Strategy pattern for audio processing:

```python
# Create an audio_processing.py file
class AudioProcessingStrategy:
    """Base class for audio processing strategies"""
    def process(self, frames, sample_rate):
        """Process audio frames and return processed data"""
        raise NotImplementedError

class WhisperAudioProcessingStrategy(AudioProcessingStrategy):
    """Audio processing strategy optimized for Whisper transcription"""
    def process(self, frames, sample_rate):
        """Process audio frames for Whisper transcription"""
        import numpy as np
        from scipy import signal
        from blaze.constants import WHISPER_SAMPLE_RATE
        
        # Convert frames to numpy array
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        
        # Resample to 16000Hz if needed
        if sample_rate != WHISPER_SAMPLE_RATE:
            logger.info(f"Resampling audio from {sample_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
            # Calculate resampling ratio
            ratio = WHISPER_SAMPLE_RATE / sample_rate
            output_length = int(len(audio_data) * ratio)
            
            # Resample audio
            audio_data = signal.resample(audio_data, output_length)
        else:
            logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
        
        # Normalize the audio data to float32 in the range [-1.0, 1.0] as expected by Whisper
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        return audio_data

class WaveFileAudioProcessingStrategy(AudioProcessingStrategy):
    """Audio processing strategy for saving to WAV files"""
    def process(self, frames, sample_rate):
        """Process audio frames for WAV file output"""
        import numpy as np
        from scipy import signal
        from blaze.constants import WHISPER_SAMPLE_RATE
        
        # Convert frames to numpy array
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        
        # Resample to 16000Hz if needed
        if sample_rate != WHISPER_SAMPLE_RATE:
            logger.info(f"Resampling audio from {sample_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
            # Calculate resampling ratio
            ratio = WHISPER_SAMPLE_RATE / sample_rate
            output_length = int(len(audio_data) * ratio)
            
            # Resample audio
            audio_data = signal.resample(audio_data, output_length)
        
        # Return as int16 for WAV file
        return audio_data.astype(np.int16)

# In recorder.py
from blaze.audio_processing import WhisperAudioProcessingStrategy, WaveFileAudioProcessingStrategy

class AudioRecorder(QObject):
    def __init__(self):
        super().__init__()
        # ...
        
        # Set default processing strategy
        self.processing_strategy = WhisperAudioProcessingStrategy()
    
    def set_processing_strategy(self, strategy):
        """Set the audio processing strategy"""
        self.processing_strategy = strategy
    
    def _process_recording(self):
        """Process the recording using the current strategy"""
        try:
            logger.info("Processing recording in memory...")
            
            # Get original sample rate
            if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
                logger.warning("No sample rate information available, assuming device default")
                if self.current_device_info is not None:
                    original_rate = int(self.current_device_info['defaultSampleRate'])
                else:
                    # If no device info is available, we have to use a reasonable default
                    original_rate = int(self.audio.get_default_input_device_info()['defaultSampleRate'])
            else:
                original_rate = self.current_sample_rate
            
            # Process audio using the strategy
            audio_data = self.processing_strategy.process(self.frames, original_rate)
            
            logger.info("Recording processed in memory")
            self.recording_finished.emit(audio_data)
        except Exception as e:
            logger.error(f"Failed to process recording: {e}")
            self.recording_error.emit(f"Failed to process recording: {e}")
    
    def save_audio(self, filename):
        """Save recorded audio to a WAV file"""
        try:
            # Use WAV file strategy for processing
            wav_strategy = WaveFileAudioProcessingStrategy()
            
            # Get original sample rate
            if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
                logger.warning("No sample rate information available, assuming device default")
                if self.current_device_info is not None:
                    original_rate = int(self.current_device_info['defaultSampleRate'])
                else:
                    # If no device info is available, we have to use a reasonable default
                    original_rate = int(self.audio.get_default_input_device_info()['defaultSampleRate'])
            else:
                original_rate = self.current_sample_rate
            
            # Process audio using the WAV strategy
            audio_data = wav_strategy.process(self.frames, original_rate)
            
            # Save to WAV file
            wf = wave.open(filename, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(WHISPER_SAMPLE_RATE)  # Always save at 16000Hz for Whisper
            wf.writeframes(audio_data.tobytes())
            wf.close()
            
            # Log the saved file location
            logger.info(f"Recording saved to: {os.path.abspath(filename)}")
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            raise
```

This pattern allows for easy extension with new audio processing strategies without modifying the recorder class.