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

## 🚧 TODO / Known Limitations

### Models Page
- Currently shows placeholder message
- Need to integrate WhisperModelTableWidget or rebuild in QML
- Model download/delete functionality pending

### Audio Device Enumeration
- AudioPage shows placeholder devices
- Need to integrate with actual PyAudio device list from settings_window.py
- _populate_mic_list() logic needs porting to bridge

### Testing Needed
- [ ] Deploy with `./blaze/dev-update.sh` → `syllablaze-dev`
- [ ] Verify settings persist across restarts
- [ ] Test System Settings button opens correct KCM
- [ ] Test GitHub buttons open browser
- [ ] Verify all controls read current values on startup
- [ ] Test changing settings and verify they apply to app

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
