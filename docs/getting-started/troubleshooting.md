# Troubleshooting Guide

This guide helps you resolve common issues with Syllablaze. If you don't find a solution here, check the [Known Issues Bug Tracker](../roadmap/Syllablaze%20Known%20Issues%20Bug%20Tracker.md) or [open an issue](https://github.com/PabloVitasso/Syllablaze/issues).

## Installation Issues

### pipx install fails - Missing portaudio

**Symptoms:**
```
error: failed to build `pyaudio`
portaudio.h: No such file or directory
```

**Solution:**

**Ubuntu/Debian:**
```bash
sudo apt install portaudio19-dev python3-dev
pipx install .
```

**Fedora:**
```bash
sudo dnf install portaudio-devel python3-devel
pipx install .
```

**Arch Linux:**
```bash
sudo pacman -S portaudio
pipx install .
```

### pipx not found

**Symptoms:**
```bash
bash: pipx: command not found
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install pipx
pipx ensurepath

# Fedora
sudo dnf install pipx
pipx ensurepath

# Arch Linux
sudo pacman -S python-pipx
pipx ensurepath
```

After installation, restart your terminal or run `source ~/.bashrc`.

### Installation succeeds but command not found

**Symptoms:**
```bash
syllablaze: command not found
```

**Diagnostic:**
```bash
pipx list  # Verify Syllablaze is installed
echo $PATH  # Check if ~/.local/bin is in PATH
```

**Solution:**
```bash
pipx ensurepath
source ~/.bashrc  # or restart terminal
```

## Audio Issues

### No audio devices found

**Symptoms:**
Settings → Audio shows "No devices available" or empty dropdown.

**Diagnostic:**
```bash
# Check PulseAudio devices
pactl list sources short

# Check ALSA devices (if not using PulseAudio)
arecord -l
```

**Solution:**

1. **Verify microphone is connected and enabled:**
   ```bash
   pavucontrol  # PulseAudio Volume Control
   # Navigate to Input Devices tab
   # Ensure microphone is not muted and volume is reasonable
   ```

2. **Restart audio services:**
   ```bash
   systemctl --user restart pipewire  # If using PipeWire
   pulseaudio --kill && pulseaudio --start  # If using PulseAudio
   ```

3. **Test microphone separately:**
   ```bash
   arecord -d 5 -f cd test.wav  # Record 5 seconds
   aplay test.wav  # Play back
   ```

### Microphone not working in Syllablaze

**Symptoms:**
Recording starts but no audio is captured, or transcription returns empty text.

**Diagnostic:**
1. Enable debug logging: Settings → About → Enable Debug Logging
2. Start recording
3. Check logs: `~/.local/state/syllablaze/syllablaze.log`
4. Look for PyAudio errors or empty audio frames

**Solution:**

1. **Check device selection:**
   - Settings → Audio → Select correct microphone
   - Test with different devices if multiple available

2. **Verify permissions (Flatpak/Snap):**
   If installed via Flatpak/Snap (not recommended, use pipx):
   ```bash
   # Grant microphone access
   flatpak permissions syllablaze
   ```

3. **Check sample rate compatibility:**
   Some devices don't support 16kHz directly. Syllablaze requires 16kHz input.
   ```bash
   # Test device capabilities
   pactl list sources | grep -A 10 "Name: your-device"
   ```

### Audio choppy or distorted

**Symptoms:**
Transcription is garbled or contains artifacts.

**Solution:**

1. **Check CPU usage:**
   High CPU usage can cause audio buffer underruns.
   ```bash
   top  # Check if syllablaze or transcription worker is using >80% CPU
   ```

2. **Reduce model size:**
   Settings → Models → Select smaller model (e.g., tiny or base instead of medium/large)

3. **Disable GPU if unstable:**
   Settings → Transcription → Compute Type → Switch from `auto` to `int8` (CPU only)

## Transcription Issues

### Model download fails

**Symptoms:**
"Failed to download model" error in Settings → Models.

**Cause:**
Network connectivity or insufficient disk space.

**Diagnostic:**
```bash
# Check disk space in cache directory
df -h ~/.cache/huggingface/

# Check network connectivity
curl -I https://huggingface.co
```

**Solution:**

1. **Verify internet connection:**
   ```bash
   ping -c 3 huggingface.co
   ```

2. **Check firewall:**
   Ensure outbound HTTPS traffic is allowed.

3. **Retry download:**
   Settings → Models → Delete incomplete model → Download again

4. **Manual download (advanced):**
   ```bash
   # Download model manually using huggingface-cli
   pip install huggingface-hub
   huggingface-cli download openai/whisper-base
   ```

### Transcription is slow

**Symptoms:**
Transcription takes >10 seconds for short recordings.

**Solution:**

1. **Enable GPU acceleration** (if NVIDIA GPU available):
   - Settings → Transcription → Compute Type → `auto`
   - Verify CUDA setup: Check logs for "CUDA available: True"

2. **Use smaller model:**
   Settings → Models → Switch to `base` or `tiny` model

3. **Check CPU usage:**
   ```bash
   htop  # Verify no other processes are consuming CPU
   ```

### Transcription returns empty text

**Symptoms:**
Recording completes but clipboard contains no text.

**Diagnostic:**
1. Check if audio was actually captured (listen to silence vs. ambient noise)
2. Enable debug logging and check for transcription errors

**Solution:**

1. **Verify microphone is capturing audio:**
   - Test with `arecord -d 5 test.wav && aplay test.wav`

2. **Check audio levels:**
   - Recording Dialog shows volume visualization
   - Ensure bars are moving during speech

3. **Verify language setting:**
   Settings → Transcription → Language → Set to correct language or "auto"

4. **Try different model:**
   Some models perform better on certain accents/languages

## Clipboard Issues

### Transcription not pasting

**Status:** Fixed in v0.5

**Symptoms:**
Text copied to clipboard but doesn't paste in other applications.

**Solution:**

1. **Update to latest version:**
   ```bash
   cd ~/dev/syllablaze
   git pull
   pipx install . --force
   ```

2. **Verify clipboard manager:**
   On Wayland, ensure a clipboard manager is running:
   ```bash
   # KDE Plasma includes Klipper by default
   klipper --version
   ```

3. **Test clipboard manually:**
   ```bash
   echo "test" | xclip -selection clipboard  # X11
   echo "test" | wl-copy  # Wayland
   ```

## Wayland-Specific Issues

### Window position not saved

**Explanation:**
Wayland compositors control window placement for security. Applications cannot programmatically set window positions.

**Status:** Known limitation, no workaround available.

**Reference:** [Wayland Support Documentation](../explanation/wayland-support.md)

**Behavior:**
- Recording dialog position saving is disabled on Wayland
- Compositor decides initial window placement
- Drag to move works, but position won't persist across sessions

### Always-on-top requires restart

**Explanation:**
KWin (KDE's window manager) requires window properties to be set during window creation. Changing `always-on-top` after creation may not take effect until the window is recreated.

**Workaround:**

**Option 1: Toggle setting twice**
1. Settings → UI → Always on top → Toggle OFF
2. Close recording dialog
3. Settings → UI → Always on top → Toggle ON
4. Open recording dialog

**Option 2: Restart application**
```bash
pkill syllablaze
syllablaze
```

**Reference:** [Wayland Support Documentation](../explanation/wayland-support.md#always-on-top-behavior)

### Recording dialog doesn't show on current desktop

**Symptoms:**
Dialog appears on a different virtual desktop when recording starts.

**Solution:**

Settings → UI → Show on all desktops → Enable

**Note:** This uses KWin D-Bus API and works reliably on Wayland.

### Window borders missing or unexpected

**Explanation:**
Wayland compositors enforce decoration policies. Frameless windows (used for recording dialog) may behave differently across compositors.

**Expected behavior:**
- Recording dialog: Circular, no borders (by design)
- Settings window: Standard window decorations
- Progress window: Standard window decorations

**If decorations are completely missing:**
Check compositor settings or KWin rules in System Settings → Window Management → Window Rules.

## Keyboard Shortcut Issues

### Global shortcut doesn't work

**Symptoms:**
Alt+Space (or custom shortcut) doesn't start recording.

**Diagnostic:**
1. Check if shortcut is registered: Settings → Shortcuts → View current shortcut
2. Enable debug logging and press shortcut
3. Check logs for "GlobalShortcuts: Key pressed" messages

**Solution:**

1. **Verify shortcut registration:**
   Settings → Shortcuts → Re-register shortcut

2. **Check for conflicts:**
   System Settings → Shortcuts → Ensure Alt+Space isn't used by another app

3. **Try different shortcut:**
   Settings → Shortcuts → Change to unused key combination (e.g., Ctrl+Alt+R)

4. **Wayland shortcut issues:**
   Ensure KDE Global Shortcuts service is running:
   ```bash
   qdbus org.kde.kglobalaccel5 /kglobalaccel org.kde.KGlobalAccel.isEnabled
   # Should return "true"
   ```

### Shortcut works once then stops

**Symptoms:**
First press works, subsequent presses don't trigger recording.

**Diagnostic:**
Check logs for stuck state:
```bash
tail -f ~/.local/state/syllablaze/syllablaze.log | grep -i "state\|shortcut"
```

**Solution:**

1. **Cancel stuck recording:**
   - Click tray icon → Stop Recording
   - Or restart application

2. **Report bug:**
   This shouldn't happen. Please [open an issue](https://github.com/PabloVitasso/Syllablaze/issues) with logs.

## UI Issues

### Settings window doesn't open

**Symptoms:**
Clicking "Settings" in tray menu does nothing, or window flashes briefly.

**Diagnostic:**
```bash
# Run from terminal to see QML errors
syllablaze
# Click Settings, watch for QML/Qt errors
```

**Solution:**

1. **Check for QML dependencies:**
   ```bash
   # Verify Kirigami is installed
   python3 -c "from PyQt6.QtQml import QQmlApplicationEngine; print('OK')"
   ```

2. **Reinstall with dependencies:**
   ```bash
   pipx install . --force
   ```

3. **Check logs:**
   `~/.local/state/syllablaze/syllablaze.log` may show QML loading errors

### Recording dialog too small/large

**Solution:**

1. **Resize with scroll wheel:**
   - Hover over dialog
   - Scroll up to enlarge, down to shrink
   - Range: 100-500 pixels

2. **Reset to default:**
   Settings → UI → Dialog Size → Set to 200 (default)

### Recording dialog stuck on screen

**Symptoms:**
Dialog visible but doesn't respond to clicks or right-click menu.

**Solution:**

1. **Dismiss via tray menu:**
   Tray icon → Dismiss Recording Dialog

2. **Restart application:**
   ```bash
   pkill syllablaze
   syllablaze
   ```

## Performance Issues

### High CPU usage during transcription

**Expected behavior:**
CPU usage spikes to 80-100% during transcription is normal, especially for larger models.

**Solution to reduce CPU usage:**

1. **Use smaller model:**
   Settings → Models → Switch to `tiny` or `base`

2. **Enable GPU acceleration:**
   If NVIDIA GPU available: Settings → Transcription → Compute Type → `auto`

3. **Close other applications:**
   Free CPU resources during transcription

### High memory usage

**Expected behavior:**
Memory usage depends on model size:
- tiny: ~500 MB
- base: ~800 MB
- small: ~1.5 GB
- medium: ~3 GB
- large: ~5 GB

**Solution:**

Use smaller model if memory is constrained.

## Getting More Help

### Enable Debug Logging

Settings → About → Enable Debug Logging

Logs location: `~/.local/state/syllablaze/syllablaze.log`

**View recent logs:**
```bash
tail -100 ~/.local/state/syllablaze/syllablaze.log
```

**Follow logs in real-time:**
```bash
tail -f ~/.local/state/syllablaze/syllablaze.log
```

### Report an Issue

If you've tried troubleshooting and the issue persists:

1. Enable debug logging
2. Reproduce the issue
3. Collect relevant log excerpt
4. [Open a GitHub issue](https://github.com/PabloVitasso/Syllablaze/issues) with:
   - Environment details (KDE version, X11/Wayland, distro)
   - Steps to reproduce
   - Expected vs actual behavior
   - Log excerpt

### Check Known Issues

Before reporting, check the [Known Issues Bug Tracker](../roadmap/Syllablaze%20Known%20Issues%20Bug%20Tracker.md) to see if it's already documented.

---

**Still stuck?** Ask in [GitHub Discussions](https://github.com/PabloVitasso/Syllablaze/discussions) for community support.
