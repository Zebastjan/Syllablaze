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