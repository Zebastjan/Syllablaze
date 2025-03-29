# Performance Optimization: Audio Processing

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