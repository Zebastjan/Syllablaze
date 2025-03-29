# Code Modularity and Cohesion

## 3.1. Improve Module Organization

**Issue:** Some functionality is not properly modularized, making the code harder to maintain.

**Example:**
The current project structure has all Python files in the same directory, mixing UI components, core functionality, and utilities:

```
blaze/
  __init__.py
  clipboard_manager.py
  constants.py
  loading_window.py
  main.py
  processing_window.py
  progress_window.py
  recorder.py
  settings.py
  settings_window.py
  transcriber.py
  volume_meter.py
  whisper_model_manager.py
  ...
```

**Solution:** Reorganize the code into more focused modules:

```
blaze/
  __init__.py
  constants.py
  main.py
  
  # UI Components
  ui/
    __init__.py
    loading_window.py
    progress_window.py
    processing_window.py
    settings_window.py
    volume_meter.py
    components.py  # For shared UI components
    
  # Core Functionality
  core/
    __init__.py
    recorder.py
    transcriber.py
    settings.py
    
  # Utilities
  utils/
    __init__.py
    audio_utils.py
    clipboard_manager.py
    whisper_model_manager.py
    ui_utils.py  # For common UI functions like centering windows
```

This reorganization would require updating imports throughout the codebase, but would result in a more maintainable structure with clear separation of concerns.

## 3.2. Extract Common UI Components

**Issue:** UI components like progress bars and status labels are duplicated across window classes.

**Example:**
```python
# In progress_window.py
self.status_label = QLabel("Recording...")
self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
layout.addWidget(self.status_label)

self.progress_bar = QProgressBar()
self.progress_bar.setRange(0, 100)
self.progress_bar.setTextVisible(True)
self.progress_bar.setFormat("%p%")
self.progress_bar.hide()
layout.addWidget(self.progress_bar)

# In processing_window.py
self.status_label = QLabel("Transcribing audio...")
layout.addWidget(self.status_label)

self.progress_bar = QProgressBar()
self.progress_bar.setRange(0, 0)  # Indeterminate progress
layout.addWidget(self.progress_bar)

# In loading_window.py
self.status_label = QLabel("Initializing...")
self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
self.status_label.setStyleSheet("color: #666;")
layout.addWidget(self.status_label)

self.progress = QProgressBar()
self.progress.setRange(0, 100)  # Set range from 0 to 100 for percentage
layout.addWidget(self.progress)
```

**Solution:** Create reusable UI components:

```python
# In ui/components.py
class StatusBar(QWidget):
    """A reusable status bar with label and progress bar"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
    def set_status(self, text):
        self.status_label.setText(text)
        
    def set_progress(self, value):
        self.progress_bar.setValue(value)
        
    def set_indeterminate(self, indeterminate=True):
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
```

Then use this component in window classes:

```python
from blaze.ui.components import StatusBar

# In window initialization
self.status_bar = StatusBar()
layout.addWidget(self.status_bar)

# Later in code
self.status_bar.set_status("Processing...")
self.status_bar.set_progress(50)
```

## 3.3. Create a Consistent Window Base Class

**Issue:** Each window class implements similar functionality (like centering, styling, etc.) in slightly different ways.

**Example:**
```python
# In progress_window.py
def __init__(self, title="Recording"):
    super().__init__()
    self.setWindowTitle(title)
    self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                       Qt.WindowType.CustomizeWindowHint |
                       Qt.WindowType.WindowTitleHint)
    # ...
    
    # Center the window
    screen = QApplication.primaryScreen().geometry()
    self.move(
        screen.center().x() - self.width() // 2,
        screen.center().y() - self.height() // 2
    )

# In loading_window.py
def __init__(self, parent=None):
    super().__init__(parent)
    self.setWindowTitle(f"Loading {APP_NAME}")
    self.setFixedSize(400, 150)
    self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
    # ...
```

**Solution:** Create a base window class with common functionality:

```python
# In ui/base_window.py
class BaseWindow(QWidget):
    """Base class for all application windows with common functionality"""
    def __init__(self, title="", parent=None, flags=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        if flags:
            self.setWindowFlags(flags)
        
    def showEvent(self, event):
        """Center the window when shown"""
        super().showEvent(event)
        from blaze.utils.ui_utils import center_window
        center_window(self)
        
    def set_app_icon(self):
        """Set the application icon"""
        self.setWindowIcon(QIcon.fromTheme("syllablaze"))
        
    def apply_app_style(self):
        """Apply consistent styling"""
        # Common styling code here
        pass
```

Then use this base class for all windows:

```python
from blaze.ui.base_window import BaseWindow

class ProgressWindow(BaseWindow):
    def __init__(self, title="Recording"):
        flags = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        super().__init__(title, flags=flags)
        self.setFixedSize(400, 320)
        self.apply_app_style()
        # Rest of initialization...
```

## 3.4. Separate Model Management UI from Logic

**Issue:** The `WhisperModelTable` class in `whisper_model_manager.py` mixes UI presentation with model management logic.

**Example:**
```python
# In whisper_model_manager.py
class WhisperModelTable(QWidget):
    model_activated = pyqtSignal(str)
    model_downloaded = pyqtSignal(str)
    model_deleted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_info = {}
        self.models_dir = ""
        self.setup_ui()
        self.refresh_model_list()
        
    # UI setup methods
    
    def on_download_model_clicked(self, model_name):
        """Download the selected model"""
        if model_name not in self.model_info:
            return
            
        info = self.model_info[model_name]
        
        # Confirm download
        if not confirm_download(model_name, info['size_mb']):
            return
            
        # Create and show download dialog
        download_dialog = ModelDownloadDialog(model_name, self)
        download_dialog.show()
        
        # Start download in a separate thread
        self.download_thread = ModelDownloadThread(model_name)
        # ... more download logic
```

**Solution:** Separate the UI from the model management logic:

```python
# In utils/whisper_model_manager.py
class WhisperModelManager:
    """Logic for managing Whisper models"""
    
    def __init__(self):
        self.model_info = {}
        self.models_dir = ""
        self.refresh_model_list()
        
    def refresh_model_list(self):
        """Refresh the model information"""
        self.model_info, self.models_dir = get_model_info()
        return self.model_info
        
    def download_model(self, model_name, progress_callback=None):
        """Download a model with progress updates"""
        # Implementation
        pass
        
    def delete_model(self, model_name):
        """Delete a model file"""
        # Implementation
        pass
        
    def activate_model(self, model_name):
        """Set a model as active in settings"""
        # Implementation
        pass

# In ui/model_table.py
class WhisperModelTableWidget(QWidget):
    """UI component for displaying and managing Whisper models"""
    model_activated = pyqtSignal(str)
    model_downloaded = pyqtSignal(str)
    model_deleted = pyqtSignal(str)
    
    def __init__(self, model_manager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.setup_ui()
        self.refresh_display()
        
    def refresh_display(self):
        """Refresh the UI with current model information"""
        model_info = self.model_manager.refresh_model_list()
        # Update UI with model_info
        
    def on_download_model_clicked(self, model_name):
        """Handle UI for model download"""
        # Show confirmation dialog
        # Show progress dialog
        # Call model_manager.download_model with progress callback
        # Emit signal when complete
```

This separation allows the model management logic to be tested independently of the UI, and makes it easier to change the UI without affecting the core functionality.