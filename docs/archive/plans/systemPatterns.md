# Syllablaze System Patterns

## Core Architecture

```
SyllablazeOrchestrator (main.py) — main controller / QSystemTrayIcon
  ├── AudioManager         → AudioRecorder (PyAudio microphone input, 16kHz)
  ├── TranscriptionManager → FasterWhisperTranscriptionWorker
  ├── UIManager            → ProgressWindow, LoadingWindow, ProcessingWindow
  ├── RecordingDialogManager → RecordingDialog.qml (circular volume indicator)
  ├── TrayMenuManager      → System tray menu creation and updates
  ├── SettingsCoordinator  → Derives backend settings from popup_style; syncs components
  ├── WindowVisibilityCoordinator → Auto-show/hide recording dialog
  ├── GPUSetupManager      → CUDA library detection and LD_LIBRARY_PATH config
  ├── GlobalShortcuts      → pynput keyboard listener (Alt+Space default)
  ├── LockManager          → Single-instance enforcement via lock file
  └── ClipboardManager     → Copies transcription result to clipboard
```

## State Management

- `ApplicationState` (`blaze/application_state.py`) is the **single source of truth**
  for recording, transcription, and dialog visibility state
- All visibility changes flow through `ApplicationState.set_recording_dialog_visible()`
- Never call `recording_dialog.show()/hide()` directly

## Settings Architecture

```
popup_style (user-facing, set via UIPage.qml)
  ├── "none"         → show_progress_window=F, show_recording_dialog=F, applet_mode=off
  ├── "traditional"  → show_progress_window=T, show_recording_dialog=F, applet_mode=off
  └── "applet"       → show_progress_window=F, show_recording_dialog=T
        ├── applet_autohide=True  → applet_mode=popup
        └── applet_autohide=False → applet_mode=persistent
```

`SettingsCoordinator._apply_popup_style()` writes the derived backend settings whenever
`popup_style` or `applet_autohide` changes.

## Settings Change Flow

```
QML settingsBridge.set(key, value)
  → Settings.set(key, value)          [validation + QSettings write]
  → SettingsBridge.settingChanged signal
  → SettingsCoordinator.on_setting_changed(key, value)
  → component update (visibility, always-on-top, derived settings, etc.)
```

## QML–Python Bridges

| Bridge | Direction | Purpose |
|---|---|---|
| `SettingsBridge` | bidirectional | Settings read/write, svgPath, model ops |
| `RecordingDialogBridge` | bidirectional | Recording toggle, volume, transcription state |
| `SvgRendererBridge` | Python→QML | SVG element bounds for precise overlay positioning |

## Key Design Decisions

- **16kHz recording**: optimized for Whisper, no resampling needed
- **In-memory processing**: no temp files written to disk
- **Qt signals/slots**: all inter-component communication is thread-safe
- **KDE kglobalaccel D-Bus**: global shortcut registration
- **Debounced persistence**: position/size changes debounced 500ms to reduce disk writes
- **Popup mode**: `applet_mode=popup` auto-shows dialog on record start,
  auto-hides 500ms after transcription via `WindowVisibilityCoordinator`

## Design Patterns

1. **Observer**: Qt signal/slot connections throughout
2. **Single source of truth**: `ApplicationState` for app state, `Settings` for config
3. **Coordinator**: `SettingsCoordinator` and `WindowVisibilityCoordinator`
4. **Manager**: 8 manager classes in `blaze/managers/` for single responsibility
5. **Bridge**: QML↔Python bridges for UI/logic separation
6. **Debounce**: Timer-based batching for position/size persistence

## KDE / Wayland Notes

- Always-on-top via `Qt.WindowType.WindowStaysOnTopHint` works on X11;
  Wayland compositor may ignore it for Tool windows
- Window position restore not reliable on Wayland (compositor controls placement)
- D-Bus integration for global shortcuts and tray icon
