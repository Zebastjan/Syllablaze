# Performance Optimization: UI Updates

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