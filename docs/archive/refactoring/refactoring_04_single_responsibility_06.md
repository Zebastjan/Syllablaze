## 2.3. Mixing UI and Business Logic in Window Classes

**Issue:** Window classes like `ProgressWindow` and `SettingsWindow` mix UI rendering with business logic.

**Example:**
```python
# In settings_window.py
def on_model_activated(self, model_name):
    """Handle model activation from the table"""
    if hasattr(self, 'current_model') and model_name == self.current_model:
        logger.info(f"Model {model_name} is already active, no change needed")
        print(f"Model {model_name} is already active, no change needed")
        return
        
    try:
        # Set the model
        self.settings.set('model', model_name)
        self.current_model = model_name
        
        # No modal dialog needed
        
        # Update any active transcriber instances
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'transcriber') and widget.transcriber:
                widget.transcriber.update_model(model_name)
        
        # Import and use the update_tray_tooltip function
        from blaze.main import update_tray_tooltip
        update_tray_tooltip()
        
        # Log confirmation that the change was successful
        logger.info(f"Model successfully changed to: {model_name}")
        print(f"Model successfully changed to: {model_name}")
                
        self.initialization_complete.emit()
    except ValueError as e:
        logger.error(f"Failed to set model: {e}")
        QMessageBox.warning(self, "Error", str(e))
```

**Solution:** Separate UI from business logic using a presenter pattern:

```python
# Create a presenter class
class SettingsPresenter:
    def __init__(self, view, settings_service):
        self.view = view
        self.settings_service = settings_service
        self.setup_connections()
        
    def setup_connections(self):
        # Connect view signals to presenter methods
        self.view.model_activated.connect(self.activate_model)
        self.view.language_changed.connect(self.change_language)
        
    def activate_model(self, model_name):
        """Handle model activation business logic"""
        try:
            # Check if already active
            if self.settings_service.get_current_model() == model_name:
                self.view.show_info(f"Model {model_name} is already active")
                return
                
            # Update the model in settings
            self.settings_service.set_model(model_name)
            
            # Notify other components via event bus
            from blaze.events import EventBus
            EventBus.instance().model_activated.emit(model_name)
            
            # Update view
            self.view.update_model_display(model_name)
            self.view.show_success(f"Model successfully changed to: {model_name}")
            
        except ValueError as e:
            self.view.show_error(f"Failed to set model: {str(e)}")

# Then in the view class
class SettingsWindow(QWidget):
    model_activated = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    
    def __init__(self, settings_service):
        super().__init__()
        self.presenter = SettingsPresenter(self, settings_service)
        self.setup_ui()
        
    def on_model_table_activated(self, model_name):
        # Just emit the signal, let the presenter handle the logic
        self.model_activated.emit(model_name)
        
    def update_model_display(self, model_name):
        # Update UI to reflect the new model
        pass
        
    def show_success(self, message):
        logger.info(message)
        print(message)
        
    def show_error(self, message):
        logger.error(message)
        QMessageBox.warning(self, "Error", message)
        
    def show_info(self, message):
        logger.info(message)
        print(message)