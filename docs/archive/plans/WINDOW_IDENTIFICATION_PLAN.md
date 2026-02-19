# Window Identification & KWin Rules Enhancement Plan

**Status:** Future Enhancement  
**Priority:** Post-refactoring  
**Created:** 2025-02-14

## Current State

### Window Matching Strategy
- **Currently using:** Window title matching (`WINDOW_TITLE = "Syllablaze Recording"`)
- **Window class:** `org.kde.python3` (default Qt/Python behavior)
- **Location:** `blaze/kwin_rules.py`

### Issues with Current Approach
1. Window title can change or be localized
2. Title matching is less precise than window class matching
3. Users see "Window settings for org.kde.python3" in KDE's window rules UI
4. Multiple Python apps would conflict if they use similar titles

## Proposed Enhancement

### 1. Global Application Identity

**Set Qt Application Properties in `blaze/main.py`:**

```python
app = QApplication(sys.argv)
app.setApplicationName("Syllablaze")
app.setOrganizationName("Syllablaze")
app.setOrganizationDomain("local.syllablaze")  # Results in: local.syllablaze.Syllablaze
```

**Benefits:**
- Window class changes from `org.kde.python3` to `local.syllablaze.Syllablaze`
- KDE's window rules UI will show "Window settings for local.syllablaze.Syllablaze"
- Proper application identity throughout KDE Plasma
- Better integration with KDE ecosystem

### 2. Window-Specific Roles for Precision

**For Recording Dialog:**
```python
# In recording_dialog_manager.py when creating the window
self.window.setWindowRole("SyllablazeRecording")
# Or via QML: window.setProperty("windowRole", "SyllablazeRecording")
```

**For Settings Window:**
```python
# In kirigami_integration.py or settings window creation
settings_window.setWindowRole("SyllablazeSettings")
```

**Benefits:**
- Different rules for different window types
- Can set different positions, behaviors per window
- More granular control in KWin rules

### 3. Updated KWin Rules Structure

**Current rule (title-based):**
```ini
[1]
Description=Syllablaze Recording - Keep Above
above=true
title=Syllablaze Recording
titlematch=1
```

**Future rule (class + role-based):**
```ini
[1]
Description=Syllablaze Recording Dialog
above=true
windowrole=SyllablazeRecording
windowrolematch=1
wmclass=local.syllablaze.Syllablaze
wmclassmatch=1
```

**Or hybrid approach (both for extra precision):**
```ini
[1]
Description=Syllablaze Recording Dialog
above=true
title=Syllablaze Recording
titlematch=1
windowrole=SyllablazeRecording
windowrolematch=1
wmclass=local.syllablaze.Syllablaze
wmclassmatch=1
```

### 4. Implementation Details

**Files to Modify:**

1. **blaze/main.py**
   - Set application name, organization name, and domain
   - This affects all windows globally

2. **blaze/recording_dialog_manager.py**
   - Set window role: `window.setProperty("windowRole", "SyllablazeRecording")`
   - Or via QML: `window.windowRole = "SyllablazeRecording"`

3. **blaze/kirigami_integration.py**
   - Set window role for settings window: `"SyllablazeSettings"`

4. **blaze/kwin_rules.py**
   - Add window class matching
   - Add window role matching
   - Update `WINDOW_TITLE` constant to include class/role options
   - Update `create_or_update_kwin_rule()` to support class/role parameters

### 5. Migration Strategy

**Backward Compatibility:**
- Keep title matching as fallback
- Gradually migrate users to new matching
- Or support both simultaneously for robustness

**User Impact:**
- Existing window rules may need recreation
- Or we can detect old rules and update them automatically
- Document in release notes

### 6. Benefits Summary

1. **Better KDE Integration**
   - Proper window class identification
   - More professional appearance in window rules UI

2. **Robust Window Matching**
   - Survives title changes
   - Multiple window types supported
   - Won't conflict with other Python apps

3. **Enhanced User Experience**
   - Clear window identification in KDE UI
   - Separate rules for different window types
   - More precise control

4. **Future-Proof**
   - Standard Qt/KDE approach
   - Works across X11 and Wayland
   - Compatible with KWin scripting

## Related Issues

- Window position persistence on Wayland
- Double-click behavior in RecordingDialog.qml
- Always-on-top window behavior

## Notes

- This is a **post-refactoring** enhancement
- Coordinate with ongoing work in recording dialog and settings UI
- Test thoroughly on both X11 and Wayland
- Consider user migration path for existing installations

## References

- KDE Window Rules documentation
- Qt QWindow::setWindowRole() documentation
- Qt QCoreApplication::setOrganizationDomain()
- KWin window matching criteria
