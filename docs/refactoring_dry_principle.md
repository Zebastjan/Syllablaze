# DRY (Don't Repeat Yourself) Principle Violations

## 1.1. Duplicated Audio Processing Logic

**Issue:** There's significant code duplication between `_process_recording()` and `save_audio()` methods in `recorder.py`.

**Example:**
```python
# In recorder.py - Duplicated code in two methods
def _process_recording(self):
    # Lines 268-301
    audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
    
    if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
        # Logic to determine sample rate
        # ...
    else:
        original_rate = self.current_sample_rate
        
    # Resampling logic
    if original_rate != WHISPER_SAMPLE_RATE:
        # Resampling code
        # ...
    else:
        logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
    
    # Normalize audio data
    audio_data = audio_data.astype(np.float32) / 32768.0
    
def save_audio(self, filename):
    # Lines 307-348
    # Almost identical code as above
    audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
    
    if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
        # Same logic to determine sample rate
        # ...
    else:
        original_rate = self.current_sample_rate
        
    # Same resampling logic
    if original_rate != WHISPER_SAMPLE_RATE:
        # Same resampling code
        # ...
    else:
        logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
```

**Solution:** Extract the common audio processing logic into a separate method:

```python
def _process_audio_data(self):
    """Process recorded audio data and return processed numpy array"""
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
        
    # Resampling logic
    if original_rate != WHISPER_SAMPLE_RATE:
        logger.info(f"Resampling audio from {original_rate}Hz to {WHISPER_SAMPLE_RATE}Hz")
        # Calculate resampling ratio
        ratio = WHISPER_SAMPLE_RATE / original_rate
        output_length = int(len(audio_data) * ratio)
        
        # Resample audio
        audio_data = signal.resample(audio_data, output_length)
    else:
        logger.info(f"No resampling needed, audio already at {WHISPER_SAMPLE_RATE}Hz")
    
    return audio_data

def _process_recording(self):
    """Process the recording and keep it in memory"""
    try:
        logger.info("Processing recording in memory...")
        audio_data = self._process_audio_data()
        
        # Normalize the audio data to float32 in the range [-1.0, 1.0] as expected by Whisper
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        logger.info("Recording processed in memory")
        self.recording_finished.emit(audio_data)
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        self.recording_error.emit(f"Failed to process recording: {e}")

def save_audio(self, filename):
    """Save recorded audio to a WAV file"""
    try:
        audio_data = self._process_audio_data()
        
        # Save to WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(WHISPER_SAMPLE_RATE)  # Always save at 16000Hz for Whisper
        wf.writeframes(audio_data.astype(np.int16).tobytes())
        wf.close()
        
        # Log the saved file location
        logger.info(f"Recording saved to: {os.path.abspath(filename)}")
        
    except Exception as e:
        logger.error(f"Failed to save audio file: {e}")
        raise
```

## 1.2. Duplicated Transcription Logic

**Issue:** There's duplication between `transcribe()` and `transcribe_file()` methods in `transcriber.py`.

**Example:**
```python
# In transcriber.py
def transcribe(self, audio_data):
    """Transcribe audio data directly from memory"""
    try:
        # Check if model needs to be reloaded due to settings changes
        self.reload_model_if_needed()
        
        # Check if language has changed
        current_language = self.settings.get('language', 'auto')
        if current_language != self.current_language:
            self.current_language = current_language
        
        # Emit progress update
        self.transcription_progress.emit("Processing audio...")
        
        # Log the language being used for transcription
        lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
        logger.info(f"Transcribing with language: {lang_str}")
        logger.info(f"Using model: {self.current_model_name}")
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

def transcribe_file(self, audio_data):
    """
    Transcribe audio data directly from memory
    
    Parameters:
    -----------
    audio_data: np.ndarray
        Audio data as a NumPy array, expected to be float32 in range [-1.0, 1.0]
    """
    if self.worker and self.worker.isRunning():
        logger.warning("Transcription already in progress")
        return
    
    # Check if model needs to be reloaded due to settings changes
    model_reloaded = self.reload_model_if_needed()
    if model_reloaded:
        logger.info("Model was reloaded due to settings change before transcription")
        print(f"Model reloaded to: {self.current_model_name}")
        
    # Check if language has changed
    current_language = self.settings.get('language', 'auto')
    if current_language != self.current_language:
        logger.info(f"Language changed from {self.current_language} to {current_language}, updating...")
        self.current_language = current_language
        print(f"Language changed to: {current_language}")
        
    # Emit initial progress status before starting worker
    self.transcription_progress.emit("Starting transcription...")
    self.transcription_progress_percent.emit(5)
        
    # Log the language being used for transcription
    lang_str = "auto-detect" if self.current_language == 'auto' else self.current_language
    logger.info(f"Transcription worker using language: {lang_str}")
    logger.info(f"Transcription worker using model: {self.current_model_name}")
    print(f"Transcribing audio with model: {self.current_model_name}, language: {lang_str}")
    
    # Use worker thread for transcription
    # ...
```

**Solution:** Extract common logic into helper methods and simplify the code:

```python
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

def transcribe_file(self, audio_data):
    """Transcribe audio data using a worker thread"""
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
    
    # Use worker thread for transcription
    # ...
```

## 1.3. Duplicated Window Positioning Logic

**Issue:** Window positioning code is duplicated across multiple window classes.

**Example:**
```python
# In progress_window.py
# Center the window
screen = QApplication.primaryScreen().geometry()
self.move(
    screen.center().x() - self.width() // 2,
    screen.center().y() - self.height() // 2
)

# In processing_window.py
# Center the window
screen = QApplication.primaryScreen().geometry()
self.move(
    screen.center().x() - self.width() // 2,
    screen.center().y() - self.height() // 2
)

# In loading_window.py
# Similar centering code
```

**Solution:** Create a utility module with a window positioning function:

```python
# Create a new file: blaze/utils.py
from PyQt6.QtWidgets import QApplication, QWidget

def center_window(window: QWidget):
    """Center a window on the screen"""
    screen = QApplication.primaryScreen().geometry()
    window.move(
        screen.center().x() - window.width() // 2,
        screen.center().y() - window.height() // 2
    )
```

Then use this in all window classes:

```python
from blaze.utils import center_window

# In window initialization
center_window(self)