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