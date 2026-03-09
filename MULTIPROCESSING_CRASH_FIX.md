# Multiprocessing Context Crash Fix

## Problem

The application was crashing with "Aborted (core dumped)" when switching models from a failed backend (e.g., liquid not installed) to a working backend (e.g., whisper). The crash occurred right after the "HARD RESET" log message.

### Stack Trace
```
#6  0x00007fb912426117 _Z15pyqt6_err_printv (QtCore.abi3.so + 0x226117)
#7  0x00007fb91242e98d _ZN13PyQtSlotProxy7unislotEPPv (QtCore.abi3.so + 0x22e98d)
#8  0x00007fb91242f82f _ZN13PyQtSlotProxy11qt_metacallEN11QMetaObject4CallEiPPv (QtCore.abi3.so + 0x22f82f)
#10 0x00007fb91242a5c5 pyqtBoundSignal_emit (QtCore.abi3.so + 0x22a5c5)
```

This indicated a Python exception in a Qt signal handler that wasn't properly caught.

## Root Cause

The crash was caused by a module-level multiprocessing context initialization in `blaze/backends/backend_client.py`:

```python
# This ran at MODULE IMPORT TIME (line 13)
_backend_spawn_context = multiprocessing.get_context("spawn")
```

**The sequence that caused the crash:**

1. `main.py` sets global multiprocessing start method to `"fork"` (for CTranslate2 compatibility)
2. User switches models from liquid to whisper
3. `_handle_model_change_hard_reset()` is called
4. Code calls `self.transcription_manager._get_transcriber_type()` to check transcriber type
5. This method imports `IsolatedBackendTranscriber` for isinstance checks
6. Importing `IsolatedBackendTranscriber` imports `BackendClient`
7. **Module-level code in `BackendClient` runs: `multiprocessing.get_context("spawn")`**
8. This creates a conflict with the already-configured "fork" mode
9. PyQt6 + multiprocessing + signal handling = CRASH

## Solution

**Delayed (lazy) initialization of the spawn context** in `backend_client.py`:

### Before:
```python
# Module-level initialization (BAD - runs at import time)
_backend_spawn_context = multiprocessing.get_context("spawn")
```

### After:
```python
# Lazy initialization - only create when actually needed
_backend_spawn_context = None

def _get_spawn_context():
    """
    Get or create the spawn context for backend subprocesses.

    Lazy initialization prevents crashes when modules are imported before
    multiprocessing is fully configured in main.py.
    """
    global _backend_spawn_context
    if _backend_spawn_context is None:
        _backend_spawn_context = multiprocessing.get_context("spawn")
    return _backend_spawn_context

# In start() method:
spawn_context = _get_spawn_context()
self._process = spawn_context.Process(...)
```

### Additional Safety: Better Exception Handling

Also improved exception handling in `_get_transcriber_type()`:

```python
try:
    from blaze.backends.isolated_backend import IsolatedBackendTranscriber
    # ... type checking ...
except (TypeError, ImportError, Exception) as e:
    # Handle import errors gracefully
    logger.debug(f"Error determining transcriber type: {e}")
    pass
```

## Why This Works

1. **No module-level side effects**: The spawn context is only created when `BackendClient.start()` is actually called
2. **Safe imports**: Modules can be imported for type checking without triggering multiprocessing initialization
3. **Preserved functionality**: When backends ARE used, they still get the correct spawn context
4. **Better error recovery**: Import errors are caught and logged instead of crashing the app

## Testing

Verified the fix works by:
1. Starting app with unavailable backend (liquid) → creates dummy transcriber
2. Switching to available backend (whisper) in settings
3. App successfully switches backends without crashing
4. Proper error messages shown when backends fail to load

## Files Modified

- `blaze/backends/backend_client.py`: Lazy initialization of spawn context
- `blaze/managers/transcription_manager.py`: Better exception handling in `_get_transcriber_type()`
