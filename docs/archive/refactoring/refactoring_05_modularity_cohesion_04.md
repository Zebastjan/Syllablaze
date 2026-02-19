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