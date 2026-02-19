# Quick Start Guide

Get started with Syllablaze in 5 minutes! This guide assumes you've already [installed Syllablaze](installation.md).

## Step 1: Launch Syllablaze

Find "Syllablaze" in your application menu (usually under "Utilities" or "Office") and launch it.

**Tip:** You can also run `syllablaze` from terminal.

The Syllablaze icon will appear in your system tray (usually top-right corner on KDE Plasma).

## Step 2: Download Whisper Model (First Run Only)

On first launch, Syllablaze needs to download a Whisper model. The default model is `base` (~150 MB).

1. Right-click tray icon → **Settings**
2. Go to **Models** page
3. Click **Download** next to the `base` model
4. Wait for download to complete (progress bar shows status)

**Tip:** You can switch to a different model later. See [Settings Reference](../user-guide/settings-reference.md#selected-model).

## Step 3: Make Your First Recording

### Using Global Shortcut (Recommended)

1. Press **Alt+Space** (default shortcut)
2. Speak clearly into your microphone
3. Press **Alt+Space** again to stop recording
4. Wait for transcription (~2-5 seconds)
5. Transcribed text is automatically copied to your clipboard
6. Paste anywhere with **Ctrl+V**

### Using Tray Icon

1. Click the Syllablaze tray icon
2. Speak into your microphone
3. Click tray icon again to stop recording
4. Text is copied to clipboard

## Step 4: Configure Settings (Optional)

Right-click tray icon → **Settings** to customize:

### Essential Settings

**Models Page:**
- Download additional models (larger = better accuracy, slower)
- Switch between models

**Audio Page:**
- Select microphone device
- Choose sample rate mode

**UI Page:**
- Choose recording indicator style:
  - **None:** No visual indicator
  - **Traditional:** Progress bar window
  - **Applet:** Circular waveform (default, recommended)

**Shortcuts Page:**
- Customize the toggle recording shortcut

## Tips for Best Results

### Microphone

- **Use a quality microphone:** Built-in laptop mics work, but external mics are better
- **Reduce background noise:** Record in a quiet environment
- **Speak clearly:** Normal speaking pace, don't rush

### Models

- **tiny:** Fastest, lowest accuracy (~1 GB disk, ~500 MB RAM)
- **base:** Good balance (default) (~2 GB disk, ~800 MB RAM)
- **small:** Better accuracy (~3 GB disk, ~1.5 GB RAM)
- **medium/large:** Best accuracy, slower (~5-10 GB disk, 3-5 GB RAM)

**Start with `base`, upgrade to `small` if accuracy isn't sufficient.**

### Languages

- Settings → Transcription → Language
- Set to your spoken language for better accuracy
- `auto` detects automatically (default)

## Recording Modes Explained

### None Mode
- No visual indicator during recording
- Monitor via tray icon color/tooltip
- Minimal distraction

### Traditional Mode
- Classic progress bar window
- Shows "Recording..." or "Transcribing..." text
- Always on top option available

### Applet Mode (Recommended)
- Circular waveform visualization
- Real-time volume bars
- Interactive:
  - **Left-click:** Toggle recording
  - **Right-click:** Context menu
  - **Drag:** Move window
  - **Scroll:** Resize
- Auto-hide option (hides when idle)

**Read more:** [Recording Modes Detailed Guide](../user-guide/recording-modes.md)

## Common First-Time Issues

### No audio devices found

**Solution:** Check microphone is connected and enabled in system settings.

```bash
pactl list sources short  # List audio sources
```

See [Troubleshooting: Audio Issues](troubleshooting.md#audio-issues).

### Transcription returns empty text

**Solution:**
1. Verify microphone is working: Record test audio with `arecord -d 5 test.wav && aplay test.wav`
2. Check audio levels in applet mode (bars should move when speaking)
3. Ensure language setting is correct

See [Troubleshooting: Transcription Issues](troubleshooting.md#transcription-issues).

### Global shortcut doesn't work

**Solution:**
1. Check shortcut isn't used by another app: System Settings → Shortcuts
2. Try different shortcut: Settings → Shortcuts → Change to Ctrl+Alt+R
3. See [Troubleshooting: Keyboard Shortcut Issues](troubleshooting.md#keyboard-shortcut-issues)

## Next Steps

Now that you've made your first recording:

- **[Settings Reference](../user-guide/settings-reference.md)** - Explore all settings
- **[Features Overview](../user-guide/features.md)** - Learn about advanced features
- **[Troubleshooting](troubleshooting.md)** - Solve common issues

---

**Enjoying Syllablaze?** Star the [GitHub repository](https://github.com/PabloVitasso/Syllablaze) and share with others!
