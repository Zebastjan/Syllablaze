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