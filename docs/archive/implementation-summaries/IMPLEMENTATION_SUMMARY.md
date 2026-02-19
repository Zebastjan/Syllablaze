# Implementation Summary: Fix Applet Interaction Issues

## Changes Made

### Phase 1: Fix Tray Menu "Open/Close Applet" Action ✅

**Problem:** Tray menu toggle didn't work because programmatic `settings.set()` doesn't emit the `settingChanged` signal that `SettingsCoordinator` listens to.

**Solution:**
- Added `settings_coordinator` parameter to `WindowVisibilityCoordinator.__init__()`
- Modified `toggle_visibility()` to manually trigger `settings_coordinator.on_setting_changed()` after setting the value
- Updated `main.py` to pass `settings_coordinator` when creating `WindowVisibilityCoordinator`

**Files Modified:**
- `blaze/managers/window_visibility_coordinator.py` (lines 11-47, 103-146)
- `blaze/main.py` (line 206)

---

### Phase 2: Fix Klipper Integration with Better Logging ✅

**Problem:** D-Bus call to Klipper failed silently with no error feedback or logging.

**Solution:**
- Enhanced `_on_open_clipboard()` with comprehensive logging (debug, info, warning levels)
- Added multiple fallback methods (qdbus, qdbus6, alternative D-Bus method names)
- Improved error messages in fallback QMessageBox
- Each D-Bus method attempt is logged with success/failure details

**Files Modified:**
- `blaze/recording_dialog_manager.py` (lines 199-267)

---

### Phase 3: Fix Clipboard Owner Window for Wayland ✅

**Problem:** Hidden clipboard owner window couldn't establish clipboard ownership on Wayland because the compositor requires a window to be mapped (shown) at least once.

**Solution:**
- Import `QTimer` and `Qt` from PyQt6.QtCore
- Added window flags: `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint`
- Added `WA_TranslucentBackground` attribute
- Set minimal size (1x1 pixels)
- Show window then hide after 100ms using `QTimer.singleShot()` to ensure mapping
- Added detailed comments explaining Wayland requirement

**Files Modified:**
- `blaze/clipboard_manager.py` (lines 1, 33-51)

---

### Phase 4: Fix Settings Window Focus on Wayland ✅

**Problem:** Settings window didn't receive focus on Wayland because `activateWindow()` is X11-specific.

**Solution:**
- Use Wayland-proper `QWindow.requestActivate()` when window handle is available
- Fall back to `raise_() + activateWindow()` for X11 or when window handle not ready
- Added logging to track which activation method is used
- Simplified logging (removed excessive debug statements)

**Files Modified:**
- `blaze/main.py` (lines 407-437)

---

### Phase 5: Implement Dismiss → Popup Mode Behavior ✅

**Problem:** Dismissing the applet (double-click or menu) had no clear behavior - should it hide temporarily or switch modes?

**Decision:** Dismiss switches from persistent to popup mode, providing better UX by auto-showing on next recording without being always-visible.

**Solution:**
- Enhanced `WindowVisibilityCoordinator.on_dialog_dismissed()` to:
  - Check current `popup_style` (only applies to "applet" style)
  - If in persistent mode (`autohide=False`), switch to popup mode (`autohide=True`)
  - Manually trigger `settings_coordinator.on_setting_changed()` (since programmatic set() doesn't emit signal)
  - If already in popup mode, just hide the dialog
- Simplified `RecordingApplet._on_dismiss_clicked()` to just emit signal (logic moved to coordinator)
- Dismiss signal was already connected to coordinator in `main.py`

**Files Modified:**
- `blaze/managers/window_visibility_coordinator.py` (lines 187-213)
- `blaze/recording_applet.py` (lines 449-457)

---

### Phase 6: Settings Window Close-and-Reopen (Already Implemented)

**Note:** The existing toggle implementation already provides close-and-reopen behavior. If settings window is open on another desktop and user clicks "Settings", it closes on first click and reopens on current desktop on second click. No additional changes needed.

---

## Testing Checklist

### 1. Tray Menu Toggle
- [ ] Right-click tray icon → "Open Applet" shows applet (persistent mode)
- [ ] Right-click tray icon → "Close Applet" hides applet (popup mode)
- [ ] Check logs confirm mode switches between popup ↔ persistent
- [ ] Verify applet actually shows/hides (not just logs)

### 2. Klipper Integration
- [ ] Middle-click on applet → Klipper history appears
- [ ] Right-click on applet → "Open Clipboard" → Klipper history appears
- [ ] If Klipper not running: fallback QMessageBox shows with clipboard content
- [ ] Check logs for detailed D-Bus method attempts

### 3. Clipboard First Use
- [ ] Fresh start of Syllablaze (kill existing instance)
- [ ] Record first transcription
- [ ] Verify text appears in clipboard immediately
- [ ] Test without toggling settings first

### 4. Settings Window Focus
- [ ] Click "Settings" from tray menu → window opens and has focus
- [ ] Click "Settings" again → window closes
- [ ] Click "Settings" third time → window opens with focus on current desktop
- [ ] Check logs for "Using QWindow.requestActivate() for Wayland" message

### 5. Dismiss Behavior
- [ ] Set applet to persistent mode (tray menu → "Open Applet")
- [ ] Double-click applet to dismiss
- [ ] Check logs confirm switch from persistent to popup mode
- [ ] Start next recording → applet auto-shows (popup mode)
- [ ] Applet auto-hides after transcription completes
- [ ] Right-click applet → "Dismiss" has same behavior as double-click

### 6. Settings Window Multi-Desktop (Manual Test)
- [ ] Open settings on desktop 1
- [ ] Switch to desktop 2
- [ ] Click "Settings" from tray → window closes
- [ ] Click "Settings" again → window opens on desktop 2

---

## Known Limitations

1. **Always-on-top toggle**: Still requires restart or toggle off/on to take effect (Wayland compositor behavior, not addressed in this fix)

2. **Window position on Wayland**: Compositor controls placement; restore may not work (not addressed in this fix)

---

---

### Bug Fix: Applet Not On All Desktops When Switching to Persistent Mode ✅

**Problem:** When switching from popup to persistent mode via settings toggle, the applet appeared but was NOT on all desktops (even though applet_onalldesktops=True). However, at startup the applet WAS correctly on all desktops.

**Root Cause:** `_apply_applet_mode()` in settings coordinator showed the applet but didn't apply the on-all-desktops setting.

**Solution:**
- Added call to `recording_dialog.update_on_all_desktops()` when entering persistent mode
- Reads the `applet_onalldesktops` setting and applies it via KWin

**Files Modified:**
- `blaze/managers/settings_coordinator.py` (lines 76-96)

---

### Bug Fix: Settings Window On All Desktops ✅

**Problem:** Settings window incorrectly appeared on all virtual desktops (should only be on current desktop).

**Root Cause:** No explicit KWin rule to prevent on-all-desktops for settings window. May have been inheriting some KDE default or existing rule.

**Solution:**
- Created `create_settings_window_rule()` function in `kwin_rules.py` to explicitly set onalldesktops=false for "Syllablaze Settings" window
- Called during settings window initialization
- Uses KWin rule with Force mode to override any defaults

**Files Modified:**
- `blaze/kwin_rules.py` (new functions: `create_settings_window_rule`, `find_or_create_settings_rule_group`)
- `blaze/kirigami_integration.py` (calls new function during init)

---

## Files Changed Summary

```
M  blaze/clipboard_manager.py
M  blaze/kirigami_integration.py
M  blaze/kwin_rules.py
M  blaze/main.py
M  blaze/managers/settings_coordinator.py
M  blaze/managers/window_visibility_coordinator.py
M  blaze/recording_applet.py
M  blaze/recording_dialog_manager.py
A  IMPLEMENTATION_SUMMARY.md
A  TESTING_GUIDE.md
```

---

## Implementation Notes

### Key Pattern: Programmatic Settings Changes Don't Emit Signals

Throughout this implementation, we discovered that `settings.set(key, value)` does **not** emit the `settingChanged` signal that `SettingsCoordinator` listens to. This signal is only emitted when settings change through the settings UI (QML bridge).

**Solution Pattern:**
```python
# Wrong - doesn't trigger coordinator
self.settings.set("applet_autohide", True)

# Correct - manually trigger coordinator
self.settings.set("applet_autohide", True)
if self.settings_coordinator:
    self.settings_coordinator.on_setting_changed("applet_autohide", True)
```

This pattern was applied in:
1. `WindowVisibilityCoordinator.toggle_visibility()` - tray menu toggle
2. `WindowVisibilityCoordinator.on_dialog_dismissed()` - dismiss action

### Wayland Clipboard Ownership

On Wayland, a window must be **mapped** (shown by compositor) at least once to establish clipboard ownership. Simply creating a hidden widget is not sufficient. The fix shows the 1x1 pixel window briefly (100ms) then hides it.

### Wayland Window Activation

On Wayland, the correct method to request window focus is `QWindow.requestActivate()`, not the X11-style `activateWindow()`. The code now checks for window handle availability and uses the appropriate method.
