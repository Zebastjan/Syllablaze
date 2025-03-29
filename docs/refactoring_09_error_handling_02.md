# Error Recovery Mechanisms

## 9.2. Missing Error Recovery Mechanisms

**Issue:** Some error handling code doesn't include proper recovery mechanisms, potentially leaving the application in an inconsistent state.

**Example:**
```python
# In recorder.py
def start_recording(self):
    if self.is_recording:
        return
        
    try:
        self.frames = []
        self.is_recording = True
        
        # Get settings
        settings = Settings()
        mic_index = settings.get('mic_index')
        sample_rate_mode = settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        
        # ... more setup code ...
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=target_sample_rate,
            input=True,
            input_device_index=mic_index,
            frames_per_buffer=1024,
            stream_callback=self._callback
        )
        
        self.stream.start_stream()
        logger.info(f"Recording started at {self.current_sample_rate}Hz")
        
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        self.recording_error.emit(f"Failed to start recording: {e}")
        self.is_recording = False  # Only this flag is reset, but other state might be inconsistent
```

**Solution:** Implement proper recovery mechanisms:

```python
# In recorder.py
def start_recording(self):
    if self.is_recording:
        return
    
    # Save original state for recovery
    original_stream = self.stream
    
    try:
        # Reset state
        self.frames = []
        self.is_recording = True
        self.stream = None
        
        # Get settings
        settings = Settings()
        mic_index = settings.get('mic_index')
        sample_rate_mode = settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        
        # ... more setup code ...
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=target_sample_rate,
            input=True,
            input_device_index=mic_index,
            frames_per_buffer=1024,
            stream_callback=self._callback
        )
        
        self.stream.start_stream()
        logger.info(f"Recording started at {self.current_sample_rate}Hz")
        
    except Exception as e:
        # Full recovery to previous state
        self._recover_from_error(original_stream)
        
        # Create and handle error
        error = RecordingError(f"Failed to start recording: {str(e)}", original_exception=e)
        handle_error(error, logger, self.recording_error)
    
def _recover_from_error(self, original_stream):
    """Recover from an error by restoring previous state"""
    logger.info("Recovering from recording error")
    
    # Reset recording state
    self.is_recording = False
    self.frames = []
    
    # Close new stream if it was created
    if self.stream and self.stream != original_stream:
        try:
            self.stream.stop_stream()
            self.stream.close()
        except Exception as e:
            logger.warning(f"Error closing stream during recovery: {e}")
    
    # Restore original stream
    self.stream = original_stream