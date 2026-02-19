## 5.4. Direct Widget Access Across Components

**Issue:** Components directly access widgets in other components, creating tight coupling.

**Example:**
```python
# In main.py
def update_volume_meter(self, value):
    # Update debug window first
    if hasattr(self, 'debug_window'):
        self.debug_window.update_values(value)
        
    # Then update volume meter as before
    if self.progress_window and self.recording:
        self.progress_window.update_volume(value)

# In settings_window.py
def on_language_changed(self, index):
    # ...
    
    # Update any active transcriber instances
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if hasattr(widget, 'transcriber') and widget.transcriber:
            widget.transcriber.update_language(language_code)
```

**Solution:** Use the event bus for communication between components:

```python
# In events.py
class EventBus(QObject):
    # ...
    volume_updated = pyqtSignal(float)  # Volume level
    # ...

# In main.py
def initialize_event_handlers(self):
    # ...
    
    # Connect recorder volume signal to event bus
    self.recorder.volume_updated.connect(self.on_volume_updated)
    
    # Connect event bus volume signal to UI update
    EventBus.instance().volume_updated.connect(self.update_volume_meter)

def on_volume_updated(self, value):
    # Forward to event bus
    EventBus.instance().volume_updated.emit(value)
    
def update_volume_meter(self, value):
    # Update volume meter if window exists
    if self.progress_window and self.recording:
        self.progress_window.update_volume(value)

# In debug_window.py
def __init__(self):
    # ...
    
    # Connect to event bus
    EventBus.instance().volume_updated.connect(self.update_values)
```

This approach decouples the components by removing direct references between them. Each component only needs to know about the event bus, not about other components.