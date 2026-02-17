# Syllablaze Progress

## Completed Work

### Core Functionality
- In-memory audio recording and transcription (no temp files)
- Faster Whisper model processing (CPU + GPU/CUDA)
- Clipboard integration
- KDE Plasma system tray + global shortcut (Alt+Space, configurable)
- Single-instance enforcement via lock file

### UI
- System tray with context menu
- Kirigami QML settings window (Models, Audio, Transcription, Shortcuts, About, UI pages)
- SVG-based circular recording dialog with radial volume visualization
- Volume-based color gradient (green→yellow→red)
- Click/drag/scroll/right-click on recording dialog
- Recording indicator settings: 3-card visual selector (None / Traditional / Applet)

### Recording Indicator Modes
- **None**: no indicator shown during recording
- **Traditional**: classic progress window (popup only)
- **Applet**: circular floating dialog
  - Auto-hide (popup): shows on record start, hides 500ms after transcription
  - Persistent: stays visible; always-on-top optional

### Architecture
- 8 manager classes in `blaze/managers/` (single responsibility)
- `ApplicationState` as single source of truth for recording/transcription/dialog state
- `WindowVisibilityCoordinator` handles all dialog auto-show/hide
- `SettingsCoordinator` derives backend settings from high-level `popup_style` setting
- Qt signals/slots for all inter-component communication (thread-safe)

### Installation
- pipx-based user install
- Desktop/icon/D-Bus integration
- GPU detection and CUDA library preloading

## Pending Work

### Near-term
- Always-on-top toggle: currently requires restart or toggle off/on to apply
- Window position persistence on X11 (Wayland compositor prevents it)

### Longer-term
- Flatpak packaging
- Transcription history
- Model benchmarking UI
- Enhanced error reporting

## Current Status
- Core functionality stable and tested (74 passing tests)
- KDE Plasma / Wayland + X11 compatible
- GPU acceleration working (CUDA via CTranslate2)
