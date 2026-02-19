# Keyboard Shortcuts

Configure global keyboard shortcuts for Syllablaze in Settings → Shortcuts.

## Default Shortcuts

| Action | Default Shortcut | Description |
|--------|------------------|-------------|
| **Toggle Recording** | Alt+Space | Start/stop recording system-wide |
| **Open Settings** | (none) | Open settings window (tray menu only) |

## Customizing Shortcuts

### Change Toggle Recording Shortcut

1. Open Settings → Shortcuts page
2. Current shortcut is displayed
3. Click **Change Shortcut** button
4. Press your desired key combination
5. Shortcut is registered immediately

**Supported modifiers:**
- Ctrl
- Alt
- Shift
- Meta (Super/Windows key)

**Examples:**
- Ctrl+Alt+R
- Meta+T
- Ctrl+Shift+Space

### Shortcut Conflicts

If your chosen shortcut is already used by another application:
- The shortcut may not work reliably
- Check System Settings → Shortcuts for conflicts
- Choose a different, unused combination

## How Global Shortcuts Work

### On KDE Plasma (Recommended)

Syllablaze uses **KGlobalAccel D-Bus API** for native KDE integration:
- Shortcuts registered with KDE's global shortcut service
- Works on both X11 and Wayland
- Integrated with System Settings → Shortcuts
- Most reliable method

### On Other Desktop Environments

Syllablaze uses **pynput keyboard listener** as fallback:
- Works on X11 and Wayland (via evdev)
- May require accessibility permissions
- Less integrated but functional

## Troubleshooting Shortcuts

### Shortcut doesn't work

**Check registration:**
- Settings → Shortcuts → Current shortcut should be displayed
- Try changing to a different shortcut

**Check for conflicts:**
- System Settings → Shortcuts → Search for your key combination
- If used by another app, choose different shortcut

**Wayland-specific:**
```bash
# Verify KGlobalAccel is running (KDE only)
qdbus org.kde.kglobalaccel5 /kglobalaccel org.kde.KGlobalAccel.isEnabled
# Should return "true"
```

See [Troubleshooting: Keyboard Shortcut Issues](../getting-started/troubleshooting.md#keyboard-shortcut-issues).

### Shortcut works once then stops

**Cause:** Application may be in stuck state (recording or transcribing).

**Solution:**
1. Click tray icon → Stop Recording
2. Wait for transcription to complete
3. Try shortcut again

If problem persists, restart Syllablaze:
```bash
pkill syllablaze
syllablaze
```

### Shortcut triggers other apps

**Cause:** Shortcut conflict with system or application shortcuts.

**Solution:**
1. System Settings → Shortcuts → Custom Shortcuts
2. Search for your shortcut key combination
3. Disable or change conflicting shortcut
4. Return to Syllablaze and re-register

## Advanced: Shortcut Behavior

### State-Dependent Behavior

| Current State | Shortcut Pressed | Action |
|---------------|------------------|--------|
| Idle | Alt+Space | Start recording |
| Recording | Alt+Space | Stop recording, begin transcription |
| Transcribing | Alt+Space | Ignored (wait for completion) |

### Shortcut Ignore Windows

Shortcuts are **ignored** during transcription to prevent:
- Accidental double-trigger
- Interrupting transcription process
- State conflicts

Wait for transcription to complete (~2-5 seconds), then shortcut becomes active again.

---

**Related Documentation:**
- [Settings Reference: Toggle Recording Shortcut](settings-reference.md#toggle-recording-shortcut)
- [Troubleshooting: Global Shortcut Issues](../getting-started/troubleshooting.md#global-shortcut-doesnt-work)
- [Design Decisions: pynput for Global Shortcuts](../explanation/design-decisions.md#pynput-for-global-shortcuts)
