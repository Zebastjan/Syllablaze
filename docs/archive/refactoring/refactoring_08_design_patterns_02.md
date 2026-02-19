## 8.2. Factory Method Pattern for UI Components

**Issue:** UI components are created directly in multiple places, making it difficult to maintain consistent styling and behavior.

**Example:**
```python
# In main.py
def toggle_recording(self):
    # ...
    # Show progress window
    if not self.progress_window:
        self.progress_window = ProgressWindow("Voice Recording")
        self.progress_window.stop_clicked.connect(self.stop_recording)
    self.progress_window.show()
    # ...

def toggle_settings(self):
    if not self.settings_window:
        self.settings_window = SettingsWindow()
    # ...

# In initialize_tray function
loading_window = LoadingWindow()
loading_window.show()
```

**Solution:** Implement a Factory Method pattern for UI components:

```python
# Create a ui_factory.py file
class UIFactory:
    """Factory for creating UI components with consistent styling and behavior"""
    
    @staticmethod
    def create_progress_window(title="Voice Recording"):
        """Create a progress window with standard configuration"""
        from blaze.ui.progress_window import ProgressWindow
        window = ProgressWindow(title)
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def create_settings_window():
        """Create a settings window with standard configuration"""
        from blaze.ui.settings_window import SettingsWindow
        window = SettingsWindow()
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def create_loading_window():
        """Create a loading window with standard configuration"""
        from blaze.ui.loading_window import LoadingWindow
        window = LoadingWindow()
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def create_processing_window():
        """Create a processing window with standard configuration"""
        from blaze.ui.processing_window import ProcessingWindow
        window = ProcessingWindow()
        # Apply common styling and configuration
        UIFactory._apply_common_window_config(window)
        return window
    
    @staticmethod
    def _apply_common_window_config(window):
        """Apply common configuration to all windows"""
        # Center the window
        from blaze.utils import center_window
        center_window(window)
        
        # Apply common styling
        window.setWindowIcon(QIcon.fromTheme("syllablaze"))
        
        # Apply any other common configuration
        # ...

# In main.py
from blaze.ui.ui_factory import UIFactory

def toggle_recording(self):
    # ...
    # Show progress window
    if not self.progress_window:
        self.progress_window = UIFactory.create_progress_window("Voice Recording")
        self.progress_window.stop_clicked.connect(self.stop_recording)
    self.progress_window.show()
    # ...

def toggle_settings(self):
    if not self.settings_window:
        self.settings_window = UIFactory.create_settings_window()
    # ...

# In initialize_tray function
loading_window = UIFactory.create_loading_window()
loading_window.show()