# Recording Dialog Verification Guide

## Quick Test (Standalone)

Test the dialog independently without the full app:

```bash
cd /home/zebastjan/syllablaze
python3 test_recording_dialog_full.py
```

**Expected behavior:**
- Circular window appears centered on screen
- Icon visible in center
- After 1.5s: Border turns red, volume ring appears and animates
- After 4.5s: Dialog grays out with "Transcribing..." overlay
- After 6s: Dialog returns to normal
- After 7.5s: Dialog hides
- After 9s: Dialog reappears
- After 10.5s: Closes

## Full Integration Test

Test with the actual Syllablaze application:

### 1. Install the updated version
```bash
pkill syllablaze
./blaze/dev-update.sh
```

### 2. Verify dialog appears on startup
- A circular window should appear centered on your screen
- It shows the Syllablaze microphone icon
- Blue border when idle

### 3. Test recording via dialog
- **Left-click** the dialog → Recording should start
- Border turns red
- Glowing ring appears around icon
- Ring pulses with your voice
- **Left-click** again → Recording stops, transcription begins
- Dialog grays out (50% opacity)
- After transcription: Dialog returns to normal

### 4. Test other interactions
- **Right-click** → Context menu appears
- **Scroll wheel** → Dialog resizes (100-500px)
- **Drag** → Dialog moves around screen
- **Middle-click** → Klipper clipboard manager opens (if available)

### 5. Test keyboard shortcut integration
- Press **Alt+Space** (or your configured shortcut)
- Dialog should update to show recording state
- Volume ring should animate

### 6. Test visibility toggle
- Right-click system tray icon
- Click "Show Recording Dialog" / "Hide Recording Dialog"
- Dialog should show/hide

## Troubleshooting

### Dialog doesn't appear on startup

Check the log:
```bash
tail -100 /tmp/syllablaze-dev.log | grep -i "recording.*dialog"
```

If you see "RecordingDialogManager: Failed to load QML window", check:
1. QML file exists: `ls blaze/qml/RecordingDialog.qml`
2. Qt6 QML modules installed: `pacman -Qs qt6-declarative`

### Dialog appears but no icon

Check icon path:
```bash
ls -la resources/syllablaze.png
```

If missing, the dialog will show but without the icon in the center.

### Volume ring doesn't animate

Ensure AudioManager is sending volume updates:
```bash
tail -f /tmp/syllablaze-dev.log | grep "volume"
```

### Recording doesn't toggle from dialog

Check if signals are connected:
```bash
tail -f /tmp/syllablaze-dev.log | grep "toggleRecording"
```

## Features Implemented

- ✅ Circular borderless window
- ✅ App icon display
- ✅ Animated volume ring (recording only)
- ✅ Transcription overlay
- ✅ Left-click: Toggle recording
- ✅ Middle-click: Open clipboard
- ✅ Right-click: Context menu
- ✅ Double-click: Dismiss
- ✅ Drag: Move window
- ✅ Scroll: Resize (100-500px)
- ✅ Size persistence
- ✅ State synchronization with app

## Files Modified

- `blaze/recording_dialog_manager.py` - NEW
- `blaze/qml/RecordingDialog.qml` - NEW
- `blaze/main.py` - MODIFIED (dialog integration)

## Future Enhancements (Not Implemented)

- Popup mode (auto-show/hide)
- Position persistence
- Fade animations
- Drop shadow effect
