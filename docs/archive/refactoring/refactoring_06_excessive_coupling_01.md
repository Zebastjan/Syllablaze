# Excessive Coupling Between Components

## 5.1. Direct Import Coupling

**Issue:** Components directly import each other, creating tight coupling.

**Example:**
```python
# In settings_window.py
from blaze.main import update_tray_tooltip

# In whisper_model_manager.py
from blaze.main import update_tray_tooltip

# In settings_window.py
def on_model_activated(self, model_name):
    # ...
    # Import and use the update_tray_tooltip function
    from blaze.main import update_tray_tooltip
    update_tray_tooltip()
```

This creates a circular dependency where:
- `main.py` imports `settings_window.py` to create the settings window
- `settings_window.py` imports `main.py` to update the tray tooltip

**Solution:** Use a signal/event system for communication:

```python
# Create an events.py file
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """Central event bus for application-wide events"""
    settings_changed = pyqtSignal(str, object)  # key, value
    model_activated = pyqtSignal(str)           # model_name
    language_changed = pyqtSignal(str)          # language_code
    recording_state_changed = pyqtSignal(bool)  # is_recording
    tooltip_update_requested = pyqtSignal()     # Request to update tooltip
    
    # Singleton instance
    _instance = None
    
    @staticmethod
    def instance():
        if EventBus._instance is None:
            EventBus._instance = EventBus()
        return EventBus._instance

# Then in settings_window.py
from blaze.events import EventBus

def on_model_activated(self, model_name):
    # ...
    self.settings.set('model', model_name)
    # Emit event instead of direct function call
    EventBus.instance().model_activated.emit(model_name)
    # Request tooltip update
    EventBus.instance().tooltip_update_requested.emit()

# In main.py
from blaze.events import EventBus

def initialize_event_handlers(self):
    # Connect to events
    EventBus.instance().model_activated.connect(self.on_model_activated)
    EventBus.instance().language_changed.connect(self.on_language_changed)
    EventBus.instance().tooltip_update_requested.connect(self.update_tooltip)
    
def on_model_activated(self, model_name):
    # Handle model activation
    pass
    
def update_tooltip(self):
    # Update tray tooltip
    pass