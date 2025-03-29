# Single Responsibility Principle Adherence

## 2.1. TrayRecorder Class Has Too Many Responsibilities

**Issue:** The `TrayRecorder` class in `main.py` handles system tray functionality, recording management, transcription management, and UI coordination.

**Example:**
```python
# In main.py
class TrayRecorder(QSystemTrayIcon):
    # This class handles:
    # 1. System tray icon and menu
    # 2. Recording state management
    # 3. Transcription coordination
    # 4. Window management (progress, settings)
    # 5. Error handling
    # 6. Application lifecycle
    # ...
```

**Solution:** Split the class into smaller, focused classes:

```python
# Proposed refactoring:

# 1. TrayIcon class - Handles only system tray functionality
class TrayIcon(QSystemTrayIcon):
    recording_toggled = pyqtSignal(bool)  # Signal when recording is toggled
    settings_toggled = pyqtSignal()       # Signal when settings is toggled
    quit_requested = pyqtSignal()         # Signal when quit is requested
    
    def __init__(self):
        super().__init__()
        self.setup_icon()
        self.setup_menu()
        
    def setup_icon(self):
        # Icon setup code
        pass
        
    def setup_menu(self):
        # Menu setup code
        pass
        
    def update_tooltip(self, info_dict):
        # Update tooltip with provided info
        pass
        
    def set_recording_state(self, is_recording):
        # Update icon and menu based on recording state
        pass