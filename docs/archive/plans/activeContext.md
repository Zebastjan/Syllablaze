# Syllablaze Active Context

## Current Version: 0.5

## Recent Work (Feb 2026)

### Recording Indicator UI Redesign (2026-02-17) ✅
- Replaced scattered Recording Dialog / Progress Window switches + ComboBox with a
  visual **3-card radio selector**: None / Traditional / Applet
- New high-level settings: `popup_style` (`"none"/"traditional"/"applet"`) and
  `applet_autohide` (bool) replace the scattered show_* booleans as the user-facing controls
- `SettingsCoordinator._apply_popup_style()` derives backend settings from these two:
  - **None** → show_recording_dialog=False, show_progress_window=False, applet_mode=off
  - **Traditional** → show_progress_window=True, show_recording_dialog=False, applet_mode=off
  - **Applet + autohide** → show_recording_dialog=True, show_progress_window=False, applet_mode=popup
  - **Applet, no autohide** → show_recording_dialog=True, show_progress_window=False, applet_mode=persistent
- `SettingsBridge.svgPath` pyqtProperty exposes the real Syllablaze SVG to QML for the Applet card preview
- UIPage.qml fully replaced: inline `StyleCard` component, GridLayout of 3 cards,
  conditional sub-options (auto-hide, size spinbox, always-on-top) below

### Orchestration Layer + Popup Mode (2026-02-17) ✅
- Added `blaze/orchestration.py` stub (RecordingController, SettingsService, WindowManager)
- `applet_mode` setting: `"off"/"persistent"/"popup"` (default: `"popup"`)
- `WindowVisibilityCoordinator` auto-shows/hides dialog via `connect_to_app_state()`
- Signal chain: `ApplicationState.recording_started` → show dialog
- Signal chain: `ApplicationState.transcription_stopped` → 500ms timer → hide dialog

### Manager Refactoring — Phase 7 (2025-02-14) ✅
- Extracted 8 manager classes to `blaze/managers/`
- main.py reduced from 1229 → ~1026 lines
- AudioManager, TranscriptionManager, UIManager, LockManager, TrayMenuManager,
  SettingsCoordinator, WindowVisibilityCoordinator, GPUSetupManager

### SVG Recording Dialog (2025-02-14) ✅
- Circular frameless QML window with radial volume visualization
- SvgRendererBridge exposes SVG element bounds to QML
- Volume-based color gradient (green→yellow→red)
- Click/drag/scroll/right-click interactions

### Bridge Consolidation — Phase 2 (2025-02-14) ✅
- Combined AudioBridge + DialogBridge → single RecordingDialogBridge
- Cleaner API, fewer context properties

### Cleanup — Phase 1 (2025-02-14) ✅
- Removed dead position-saving code, deleted unused files
- Position persistence intentionally disabled (KDE/Wayland limitation)

## Current State

### Known Issues
- **Always-on-top toggle**: Requires restart or toggle off/on to take effect (minor, deferred)
- **Clipboard**: Previously intermittent failure appears resolved — monitoring

### Settings Architecture
```
popup_style (user-facing)
  └─ none         → show_progress_window=F, show_recording_dialog=F, applet_mode=off
  └─ traditional  → show_progress_window=T, show_recording_dialog=F, applet_mode=off
  └─ applet       → show_progress_window=F, show_recording_dialog=T
       └─ applet_autohide=True  → applet_mode=popup
       └─ applet_autohide=False → applet_mode=persistent
```

### Visibility Control Pattern
- All visibility changes go through `ApplicationState.set_recording_dialog_visible()`
- Never call `recording_dialog.show()/hide()` directly
- `WindowVisibilityCoordinator` is the single consumer of visibility signals

## Pending Work

### Near-term
- Always-on-top toggle fix (requires restart currently)
- Window position persistence on X11 (Wayland compositor prevents it)

### Longer-term
- Flatpak packaging
- Transcription history
- Model benchmarking UI
- Enhanced error reporting
