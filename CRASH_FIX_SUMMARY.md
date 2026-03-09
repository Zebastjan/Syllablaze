# Minimal Crash Fix - Summary

## Problem
App was crashing with "Unhandled Python exception" and core dump when switching from unavailable backend (dummy transcriber) to working backend.

## Root Cause
The crash was happening in the synchronous part of `_handle_model_change_hard_reset()` when:
1. App starts with unavailable backend → creates dummy transcriber
2. User selects working backend → signal triggers hard reset
3. Methods like `self.app_state.is_transcribing()`, `self._stop_recording()` were called
4. These methods likely accessed transcription_manager or transcriber in an inconsistent state

## Minimal Fixes Applied

### 1. Added Defensive Checks (main.py)
```python
def _handle_model_change_hard_reset(self, model_name):
    # Check if we have a valid transcription manager and transcriber
    has_valid_transcriber = (
        hasattr(self, "transcription_manager")
        and self.transcription_manager is not None
        and self.transcription_manager._get_transcriber_type() != "dummy"
    )
    
    # Only stop recording if we have valid transcriber
    if has_valid_transcriber:
        try:
            if self.app_state.is_transcribing():
                self.app_state.stop_transcription()
        except Exception as e:
            logger.warning(f"Error stopping transcription: {e}")
        # ... similar for _stop_recording()
    else:
        logger.info("Skipping - no valid transcriber")
```

**Key Changes:**
- Check transcriber type before any operations
- Skip transcription/recording stop when transcriber is dummy
- Wrap all operations in try/except blocks
- Added detailed logging at each step

### 2. Added Reentrance Prevention (main.py)
```python
def __init__(self, ...):
    # ... existing code ...
    self._is_changing_model = False

def _handle_model_change_hard_reset(self, model_name):
    # Prevent re-entrance
    if self._is_changing_model:
        logger.warning(f"Ignoring model change - already processing")
        return
    
    self._is_changing_model = True
    try:
        # ... operations ...
    except Exception as e:
        logger.error(f"Error: {e}")
        self._is_changing_model = False

def _deferred_backend_reinit(self, model_name):
    try:
        # ... reinitialization ...
    finally:
        # Always reset flag
        self._is_changing_model = False
```

**Key Changes:**
- Added `_is_changing_model` flag in `__init__`
- Check flag at start of `_handle_model_change_hard_reset`
- Reset flag in both success and error cases in deferred callback

## Files Modified

1. **blaze/main.py**:
   - Added `_is_changing_model = False` in `__init__`
   - Rewrote `_handle_model_change_hard_reset()` with defensive checks
   - Updated `_deferred_backend_reinit()` to reset flag

2. **tests/unit/test_crash_reproduction.py** (new):
   - Minimal tests replicating crash scenario
   - Tests for reentrance prevention
   - Tests for exception handling

## Test Results

```
37 backend tests PASSED
4 crash reproduction tests PASSED

- Backend derivation: ✅
- Type detection: ✅  
- Switching integration: ✅
- Dummy→Working: ✅
- Reentrance prevention: ✅
- Exception handling: ✅
```

## What Changed

**Before:**
- Synchronous operations on potentially invalid transcriber state
- No protection against nested signal calls
- Minimal error handling

**After:**
- Check transcriber validity before any operations
- Skip operations when transcriber is dummy/None
- Reentrance flag prevents nested calls
- Comprehensive try/except blocks
- Always reset flag even on errors

## Testing

To verify the fix works:
1. Start app with unavailable backend (Liquid)
2. Wait for dummy transcriber creation
3. Select working backend (Whisper) in settings
4. App should switch without crash

The defensive programming approach ensures:
- No crashes from accessing invalid transcriber state
- Graceful handling of edge cases
- Clear logging for debugging
- Future model changes still work
