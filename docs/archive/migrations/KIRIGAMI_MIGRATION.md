# Kirigami UI Migration

## Overview

Syllablaze has migrated from PyQt6 widgets to Kirigami QML for the settings UI. This provides a modern, native KDE experience that matches the Plasma desktop environment.

## Changes Made

### 1. New Kirigami Settings UI (`blaze/kirigami_integration.py`)

- **KirigamiSettingsWindow**: Replaces old PyQt6 SettingsWindow
- **SettingsBridge**: Python-QML bridge using pyqtSlot decorators
- **ActionsBridge**: Handles actions like opening URLs and system settings
- **QML UI**: All UI defined in `blaze/qml/` directory

### 2. Installation Changes (`install.py`)

- Added `--system-site-packages` flag to pipx install
- This allows access to system Qt6/Kirigami modules
- Fixes the "module 'org.kde.kirigami' is not installed" error

### 3. Main Application (`blaze/main.py`)

- Already imports `KirigamiSettingsWindow as SettingsWindow`
- No changes needed - integration was already done
- Sets `QML2_IMPORT_PATH` environment variable

### 4. Features Implemented

**Models Page:**
- Download/delete/activate Whisper models
- Real-time download progress with threaded operations
- Automatic size calculation for downloaded models (handles both .pt files and directories)
- Size display in MB/GB with intelligent formatting
- Visual indicators for active/downloaded models

**Audio Page:**
- Real microphone device enumeration via PyAudio
- Intelligent blocklist filtering (removes virtual/system devices)
- System default microphone option
- Sample rate mode selection (Whisper-optimized vs Device-native)

**Transcription Page:**
- Language selection with auto-detect
- Compute type (int8, float16, float32)
- Device selection (CPU, CUDA)
- Beam size configuration
- VAD filter and word timestamps toggles

**Shortcuts Page:**
- Displays current KDE global shortcut
- Reads from kglobalshortcutsrc
- Button to open KDE System Settings for shortcut configuration

**About Page:**
- Application version and description
- GitHub repository link
- KDE resources links

### 5. Window Scaling

- Proportional scaling based on 4K baseline (900×616 @ 3840×2160)
- Scales down for lower resolutions
- Min/max size constraints: 600×400 to 1200×900

## Old Code (Deprecated)

- `blaze/settings_window.py` - Old PyQt6 widget-based UI (no longer imported)
- Can be removed in future cleanup

## Testing

### Development Testing

```bash
# Test Kirigami UI directly (uses system Python with Kirigami)
./test_kirigami.sh
```

### Production Testing

```bash
# Uninstall old version
pipx uninstall syllablaze

# Install new version with system-site-packages
python3 install.py

# Run application
syllablaze

# Test settings window
# Right-click tray icon → Settings
```

## Requirements

### System Dependencies

- KDE Plasma 5.27+ or 6.x
- Qt6 6.5+
- Kirigami 6.0+
- PyQt6 (system package recommended)

### Python Dependencies

- PyQt6 >= 6.6.0
- PyQt6-Qt6 (bundled with PyQt6, but system Qt/Kirigami preferred)
- All other requirements in requirements.txt

## Known Issues

### Fixed

- ✅ Kirigami modules not loading in pipx (fixed with --system-site-packages)
- ✅ large-v3-turbo showing 0 MB (fixed by handling both files and directories)
- ✅ Screen undefined error in QML (fixed with null check)
- ✅ Too many non-microphone audio devices (fixed with comprehensive blocklist)

### Outstanding

- Settings window doesn't work with old `syllablaze` package (needs reinstall with new install.py)
- Old PyQt6 settings_window.py still in codebase (can be removed)

## Migration Path

1. **For users with existing installation:**
   ```bash
   pipx uninstall syllablaze
   python3 install.py
   ```

2. **For new installations:**
   ```bash
   python3 install.py
   ```

3. **Existing settings are preserved** (uses QSettings in ~/.config/)

## Architecture

```
User clicks Settings → ApplicationTrayIcon.toggle_settings()
  ↓
Creates KirigamiSettingsWindow instance
  ↓
QQmlApplicationEngine loads SyllablazeSettings.qml
  ↓
QML imports org.kde.kirigami (via system Qt)
  ↓
QML pages interact with Python via SettingsBridge/ActionsBridge
  ↓
Settings persisted via QSettings
```

## Future Work

- Remove deprecated settings_window.py
- Add more settings pages (appearance, advanced)
- Implement native KDE shortcuts integration (see plan in system reminders)
- Add keyboard navigation improvements
- Consider packaging as Flatpak or AppImage with bundled Kirigami
