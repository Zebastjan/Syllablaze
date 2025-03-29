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