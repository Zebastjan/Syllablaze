# Development Guide - Syllablaze

This document provides technical context for developers and AI coding assistants working on Syllablaze.

## Current Development Focus (Feb 2025)

We're actively working on **recording dialog settings persistence and window behavior**. This involves:

1. Making window position/size/always-on-top settings persist correctly across sessions
2. Ensuring visibility state synchronizes between QML UI, Python code, and system tray menu
3. Handling Wayland/X11 differences in window flag behavior

See CLAUDE.md "Known Issues & Ongoing Work" section for detailed status.

## Architecture Deep Dive

### Python-QML Communication Patterns

**Pattern 1: State Exposure (Python → QML)**
```python
# Python: Define Qt property with change signal
class AudioBridge(QObject):
    volumeChanged = pyqtSignal(float)

    @pyqtProperty(float, notify=volumeChanged)
    def currentVolume(self):
        return self._current_volume
```

```qml
// QML: Bind to property, reacts automatically
opacity: (audioBridge && audioBridge.currentVolume > 0.8) ? 0.5 : 1.0
```

**Pattern 2: Action Invocation (QML → Python)**
```python
# Python: Define slot to receive calls from QML
class DialogBridge(QObject):
    toggleRecordingRequested = pyqtSignal()

    @pyqtSlot()
    def toggleRecording(self):
        self.toggleRecordingRequested.emit()
```

```qml
// QML: Call Python method directly
onClicked: dialogBridge.toggleRecording()
```

**Pattern 3: Bidirectional Settings Sync**
```python
# Python: Generic get/set with change notifications
class SettingsBridge(QObject):
    settingChanged = pyqtSignal(str, 'QVariant')  # key, value

    @pyqtSlot(str, 'QVariant')
    def set(self, key, value):
        Settings().set(key, value)
        self.settingChanged.emit(key, value)
```

```qml
// QML: Listen for changes from ANY source (Python, other UI)
Connections {
    target: settingsBridge
    function onSettingChanged(key, value) {
        if (key === "show_recording_dialog") {
            showDialogSwitch.checked = value
        }
    }
}
```

### Recursion Prevention Pattern

**Problem**: Setting change triggers UI update, which triggers setting change, infinite loop.

**Solution**: Guard flag to detect and prevent recursive updates.

```python
# In main.py
def _on_setting_changed(self, key, value):
    if key == "show_recording_dialog":
        # Prevent recursive updates
        if self._updating_dialog_visibility:
            logger.debug("Skipping visibility update (already in progress)")
            return

        self._updating_dialog_visibility = True
        try:
            self.set_recording_dialog_visibility(value, source="settings_change")
        finally:
            self._updating_dialog_visibility = False
```

### Window Flag Management (Wayland vs X11)

**Challenge**: Different behavior on Wayland vs X11 for always-on-top windows.

**Qt.WindowType.Tool behavior**:
- X11: Can control stay-on-top with `WindowStaysOnTopHint`
- Wayland: ALWAYS stays on top (compositor security feature)

**Solution**: Use `Qt.WindowType.Window` instead of `Qt.WindowType.Tool`

```python
# Better control on both X11 and Wayland
base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
if always_on_top:
    new_flags = base_flags | Qt.WindowType.WindowStaysOnTopHint
else:
    new_flags = base_flags  # Will NOT stay on top
```

**Fallback for Wayland**: KWin window rules (`blaze/kwin_rules.py`)
- Uses `kwriteconfig6` to write rules to `~/.config/kwinrulesrc`
- Can force "keep above" behavior at compositor level
- Not yet integrated (pending testing)

### Settings Persistence Strategy

**Storage**: QSettings (INI format) at `~/.config/syllablaze/syllablaze.conf`

**Type Handling**:
- QSettings stores everything as QVariant
- Booleans need explicit conversion on read: `bool(settings.get(key, default))`
- Numbers stored as strings, converted on read: `int(settings.get(key, default))`

**Validation Pattern**:
```python
def set(self, key, value):
    # Validate and clamp
    if key == "recording_dialog_size":
        value = max(100, min(500, int(value)))

    # Store
    self.settings.setValue(key, value)

    # Notify
    self.setting_changed.emit(key, value)
```

**Debouncing Pattern** (for window position/size):
- QML: Use Timer to delay save after drag/resize stops
- Prevents excessive disk writes during drag operations
- 500ms delay is good balance between responsiveness and performance

```qml
Timer {
    id: positionSaveTimer
    interval: 500  // 500ms after user stops moving
    onTriggered: {
        dialogBridge.saveWindowPosition(root.x, root.y)
    }
}

onXChanged: {
    if (root.visible) {
        positionSaveTimer.restart()  // Restart timer on each move
    }
}
```

## Testing Strategies

### Manual Testing Checklist for Recording Dialog

**Settings Persistence**:
1. ✅ Resize dialog with scroll wheel → restart app → size restored
2. ⏳ Move dialog to corner → restart app → position restored (Wayland: may not work)
3. ✅ Toggle always-on-top → verify window behavior changes
4. ✅ Toggle visibility in settings → verify dialog shows/hides

**Visibility Synchronization**:
1. ✅ Hide dialog via double-click → settings UI unchecks automatically
2. ✅ Show dialog via settings UI → dialog appears
3. ✅ Hide via settings UI → verify no errors in logs
4. ✅ System tray menu state matches settings UI state

**User Interactions**:
1. ✅ Single-click toggles recording (not double-click action)
2. ✅ Double-click dismisses dialog
3. ✅ Right-click shows context menu
4. ✅ Drag moves window smoothly
5. ✅ Scroll wheel resizes (100-500px range enforced)
6. ✅ No accidental clicks within 300ms of dialog appearing

### Log Patterns to Check

**Good patterns** (expected):
```
INFO:blaze.recording_dialog_manager:DialogBridge: saveWindowPosition(1234, 567) called from QML
INFO:blaze.recording_dialog_manager:RecordingDialogManager: Saved window position from QML (1234, 567)
INFO:blaze.settings:Setting changed: recording_dialog_x = 1234
INFO:blaze.main:set_recording_dialog_visibility(visible=True, source=settings_ui)
```

**Bad patterns** (bugs):
```
ERROR: 'NoneType' object has no attribute 'isRecording'  # Missing null checks in QML
WARNING: Recursive visibility update detected  # Recursion prevention not working
WARNING: Position never saved  # QML handlers not firing
```

## Common Pitfalls

### QML Signal Connections Don't Work from Python

**Problem**: Trying to connect to QML property changes from Python
```python
# DOESN'T WORK - xChanged is QML-only signal
self.window.xChanged.connect(self._on_position_changed)
```

**Solution**: Use QML `onXChanged` handler to call Python slot
```qml
onXChanged: {
    dialogBridge.saveWindowPosition(root.x, root.y)
}
```

### Window Flags Must Be Set Before First Show

**Problem**: Setting flags in `show()` causes border flash on first show
```python
def show(self):
    self.window.setFlags(Qt.WindowType.FramelessWindowHint)  # Too late!
    self.window.show()
```

**Solution**: Set flags in `initialize()` after window creation
```python
def initialize(self):
    self.window = root_objects[0]
    self.window.setFlags(Qt.WindowType.FramelessWindowHint)  # Before first show
```

### QSettings Returns Strings for Numbers

**Problem**: Reading numeric settings returns strings
```python
size = settings.get("recording_dialog_size", 200)
# size is "200" (string), not 200 (int)
self.window.setProperty("width", size)  # TypeError!
```

**Solution**: Always convert types explicitly
```python
size = int(settings.get("recording_dialog_size", 200))
```

## File Organization

### Core Application (`blaze/`)
- `main.py` - Entry point, ApplicationTrayIcon orchestrator, centralized visibility control
- `settings.py` - QSettings wrapper with validation and type conversion
- `constants.py` - App version, sample rates, model names, defaults

### Managers (`blaze/managers/`)
- `audio_manager.py` - Audio recording lifecycle
- `transcription_manager.py` - Whisper transcription
- `ui_manager.py` - Progress/loading/processing windows
- `lock_manager.py` - Single-instance enforcement

### Recording Dialog (`blaze/`)
- `recording_dialog_manager.py` - RecordingDialogManager, AudioBridge, DialogBridge
- `qml/RecordingDialog.qml` - Circular dialog UI with volume visualization

### Settings UI (`blaze/`)
- `kirigami_integration.py` - KirigamiSettingsWindow, SettingsBridge, ActionsBridge
- `qml/SyllablazeSettings.qml` - Main settings window
- `qml/pages/ModelsPage.qml` - Model download/deletion
- `qml/pages/AudioPage.qml` - Input device, sample rate
- `qml/pages/TranscriptionPage.qml` - Language, prompt
- `qml/pages/ShortcutsPage.qml` - Keyboard shortcuts (read-only)
- `qml/pages/AboutPage.qml` - App info, links
- `qml/pages/UIPage.qml` - Dialog/window visibility and behavior settings

### Window Rules (Not Yet Integrated)
- `kwin_rules.py` - KWin compositor window rules for Wayland always-on-top fallback

## Next Steps for Contributors

If you're picking up work on the recording dialog settings:

1. **Test current implementation**: Run `./blaze/dev-update.sh` and test the checklist above
2. **Check logs**: Look for the "good patterns" and "bad patterns" listed in this guide
3. **Read uncommitted changes**: Use `git diff` to see the latest work on main.py, recording_dialog_manager.py
4. **Fix remaining issues**: See CLAUDE.md "Known Issues & Ongoing Work" for status
5. **Integration work**: Consider integrating `kwin_rules.py` as fallback for Wayland always-on-top

## Useful Commands

```bash
# Watch live logs during testing
tail -f ~/.local/state/syllablaze/syllablaze.log

# Check settings file
cat ~/.config/syllablaze/syllablaze.conf

# Reset all settings (for testing)
rm ~/.config/syllablaze/syllablaze.conf
pkill syllablaze
syllablaze

# Force reload KWin rules (if using kwin_rules.py)
qdbus org.kde.KWin /KWin reconfigure
```
