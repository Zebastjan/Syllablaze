# Recording Dialog Cleanup - Phase 1 Complete

**Date:** 2025-02-14  
**Status:** ✅ Complete  
**Scope:** Remove dead position-saving code and clean up architecture

## Summary

Successfully removed all dead position-saving code from the recording dialog system. The position persistence feature was disabled due to KDE/Wayland limitations, but the code remained as no-ops. This cleanup removes ~50 lines of dead code and simplifies the architecture.

## Changes Made

### 1. Files Removed
- `blaze/qml/RecordingDialogNew.qml` - Old prototype from earlier work
- `blaze/kde_window_manager.py` - Unused KWindowSystem wrapper
- `blaze/kwin_window_tracker.py` - Non-functional KWin script approach

### 2. recording_dialog_manager.py Changes

**Removed:**
- `is_wayland` import (no longer needed)
- `DialogBridge.windowPositionChanged` signal
- `DialogBridge.saveWindowPosition(x, y)` method
- `DialogBridge.isWayland()` method
- `RecordingDialogManager._kde_window_manager` attribute
- Position-related signal connection in `__init__`
- `_restore_window_position()` method (was no-op)
- `_on_window_position_changed_from_qml()` method (was no-op)

**Kept:**
- `AudioBridge` - Audio state management
- `DialogBridge` - User actions (toggle, open clipboard, etc.)
- `saveWindowSize()` - Size persistence still works
- `getWindowSize()` - Size restoration still works

### 3. RecordingDialog.qml Changes

**Removed:**
- Position tracking timers
- `onXChanged`/`onYChanged` handlers
- Position save calls to bridge

**Kept:**
- Size tracking on scroll wheel
- All mouse interactions (click, drag, right-click)
- Visual feedback (volume, recording state)

## Current Architecture (Clean)

```
RecordingDialogManager
├── AudioBridge (READ-ONLY)
│   ├── isRecording → ApplicationState
│   ├── isTranscribing → ApplicationState
│   ├── currentVolume (audio-specific)
│   └── audioSamples (audio-specific)
└── DialogBridge (ACTIONS)
    ├── toggleRecording() → emit signal
    ├── openClipboard() → emit signal
    ├── openSettings() → emit signal
    ├── dismissDialog() → emit signal
    ├── saveWindowSize(size) → Settings + KWin
    └── getWindowSize() → Settings
```

## Size Persistence Still Works

Window size is still persisted via:
1. KWin rules (saved to `~/.config/kwinrulesrc`)
2. QSettings fallback (`recording_dialog_size`)
3. Scroll wheel resize triggers save

Position persistence is **intentionally removed** - KDE/Wayland doesn't support it reliably.

## Future Work

This cleanup prepares the codebase for:
1. New visualizer dialog with SVG design
2. Dialog mode switching (legacy / visualizer / disabled)
3. Clean bridge consolidation (AudioBridge + DialogBridge → RecordingDialogBridge)
4. Component-based QML architecture

## Testing

After this cleanup, verify:
- [ ] Dialog shows/hides correctly
- [ ] Scroll wheel resizes window
- [ ] Size is saved and restored
- [ ] All mouse interactions work (click, drag, right-click)
- [ ] No position-related errors in logs

## Notes for Claude

- Position code intentionally removed, not just disabled
- KWin rules still manage always-on-top behavior
- Size persistence is the only window geometry we support
- Architecture is now cleaner for the new visualizer dialog
