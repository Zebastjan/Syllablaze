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