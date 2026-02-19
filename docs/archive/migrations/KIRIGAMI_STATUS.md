# Kirigami UI Status

## ✅ Complete and Working

### UI Framework
- [x] Native Kirigami.ApplicationWindow with KDE theme integration
- [x] Sidebar navigation (Models, Audio, Transcription, Shortcuts, About)
- [x] Page loader with smooth transitions
- [x] Proper Kirigami components (Card, FormLayout, InlineMessage, etc.)

### Python-QML Bridge
- [x] SettingsBridge - Full settings read/write
- [x] ActionsBridge - URL opening, System Settings launcher
- [x] QML context properties (APP_NAME, APP_VERSION, GITHUB_REPO_URL)
- [x] Signal emission for live updates

### Settings Pages

**Audio** ✅
- Input device selection (placeholder data for now)
- Sample rate mode (16kHz Whisper vs Device default)
- Settings persist to QSettings
- Info message about 16kHz optimization

**Transcription** ✅
- Language selection (auto-detect + 11 languages)
- Compute type (float32/float16/int8)
- Device (CPU/CUDA)
- Beam size (1-10)
- VAD filter toggle
- Word timestamps toggle
- All settings save immediately

**Shortcuts** ✅
- Current shortcut display (reads from QSettings)
- "Configure in System Settings" button (launches systemsettings kcm_keys)
- Info card about kglobalaccel integration
- Native KDE integration messaging

**About** ✅
- App name + version (from Python constants)
- Feature list with checkmarks
- GitHub Repository button (working)
- Report Issue button (working)
- Professional card layout

## ⚠️ Known Issue: Kirigami Module Loading

**Status**: Kirigami UI works in test mode but not in pipx-installed app

**Root Cause**: PyQt6 installed via pipx includes its own bundled Qt6 libraries (PyQt6-Qt6) that don't include Kirigami QML modules. System Kirigami is installed for system Qt6, creating a mismatch.

**Workarounds**:
1. **Use test script** (recommended for development):
   ```bash
   ./test_kirigami.sh
   ```
   - Uses system Python + system PyQt6 + system Qt6
   - Has access to system Kirigami modules
   - Isolated settings (won't affect running app)

2. **Run directly with system Python**:
   ```bash
   python3 -m blaze.main
   ```
   - Uses system PyQt6 and Kirigami
   - Shares settings with production app

**Attempted Solutions** (did not work):
- Setting QML2_IMPORT_PATH environment variable
- Calling engine.addImportPath() programmatically
- Symlinking system Kirigami modules into venv Qt directory
  (Kirigami has C++ plugin dependencies that can't just be symlinked)

**Proper Solution** (TODO):
- Modify install.py to use pipx `--system-site-packages` flag
- Skip installing PyQt6 in venv, use system PyQt6 instead
- This gives access to system Qt6 and all KDE modules

## 🚧 TODO / Known Limitations

### Models Page
- Currently shows placeholder message
- Need to integrate WhisperModelTableWidget or rebuild in QML
- Model download/delete functionality pending

### Audio Device Enumeration
- AudioPage shows placeholder devices
- Need to integrate with actual PyAudio device list from settings_window.py
- _populate_mic_list() logic needs porting to bridge

### Testing Status
- [x] **System Settings button** (sidebar footer) - Opens kcmshell6 successfully
- [x] **About page layout** - All 7 features properly contained in card
- [x] Settings persist across restarts (verified in test mode)
- [x] GitHub buttons open browser correctly
- [x] Controls read current values on startup
- [x] Settings changes save and apply correctly
- [ ] Deploy to syllablaze-dev (blocked by Kirigami module issue)
- [ ] Full integration testing with production app

## How to Test

```bash
# Standalone test (isolated - uses separate QSettings)
./test_kirigami.sh

# Deploy to syllablaze-dev
./blaze/dev-update.sh  # auto-detects kirigami-rewrite branch

# Run dev version
syllablaze-dev
```

**Note**: The test script (`./test_kirigami.sh`) uses isolated QSettings (organization: "KDE-Testing") so it won't interfere with your running Syllablaze instance.

## Architecture

```
KirigamiSettingsWindow (Python)
  ├── QQmlApplicationEngine
  ├── SettingsBridge (QObject)
  │   └── Settings() instance
  └── ActionsBridge (QObject)

SyllablazeSettings.qml (Main Window)
  ├── Sidebar (category list)
  └── Content Area (page loader)
      ├── pages/AudioPage.qml
      ├── pages/TranscriptionPage.qml
      ├── pages/ShortcutsPage.qml
      ├── pages/AboutPage.qml
      └── pages/ModelsPage.qml (TODO)
```

## Next Steps

1. **Model Management** — Either:
   - Port WhisperModelTableWidget to QML (native Kirigami list)
   - Or embed PyQt6 widget in QML (hybrid approach)

2. **Audio Device Integration** — Wire up real device list:
   - Add `refreshAudioDevices()` slot to SettingsBridge
   - Call settings_window's `_populate_mic_list()` logic
   - Return filtered device list to QML

3. **Polish**:
   - Add loading indicators for async operations
   - Add confirmation dialogs for destructive actions
   - Add keyboard navigation shortcuts

4. **Integration Testing**:
   - Test with actual Whisper models
   - Verify GPU detection
   - Test recording with different devices
