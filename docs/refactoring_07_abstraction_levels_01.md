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