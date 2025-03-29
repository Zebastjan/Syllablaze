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