# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Syllablaze is a PyQt6 system tray application for real-time speech-to-text transcription using OpenAI's Whisper (via faster-whisper). It records audio, transcribes it, and copies the result to clipboard. Targets KDE Plasma on Wayland/X11 Linux desktops. Installed as a user-level package via pipx.

## Current Development Status

**Active Development Areas** (as of Feb 2025):
- Recording dialog settings persistence and window behavior
- Visibility synchronization between UI components
- Wayland/X11 compatibility for always-on-top behavior

See "Known Issues & Ongoing Work" section below for details.

## Build and Run Commands

```bash
# Install (user-level via pipx)
python3 install.py

# Run directly during development
python3 -m blaze.main

# Dev update: copies to pipx install dir, restarts app
# NOTE: Ruff has been DISABLED during debugging sessions
./blaze/dev-update.sh

# Uninstall
python3 uninstall.py
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_audio_processor.py

# Run specific test
pytest tests/test_audio_processor.py::test_frames_to_numpy

# Run by marker: unit, integration, audio, ui, settings, core
pytest -m audio
```

pytest config is in `tests/pytest.ini`. Fixtures and mocks (MockPyAudio, MockSettings, sample audio data) are in `tests/conftest.py`.

## Linting

CI uses **flake8** (max-line-length=127, max-complexity=10). Dev workflow uses **ruff** optionally. No formatter (black/autopep8) is configured.

```bash
flake8 . --max-line-length=127
# ruff check blaze/ --fix  # DISABLED during active debugging
```

## Architecture

**Entry point**: `blaze/main.py` - `main()` function creates the Qt application, initializes `SyllablazeOrchestrator` (the main controller), sets up D-Bus service (`SyllaDBusService`), and starts a qasync event loop.

**Core flow**:
```
SyllablazeOrchestrator (main.py) - orchestrator
  ├── AudioManager -> AudioRecorder (recorder.py) -> PyAudio microphone input
  ├── TranscriptionManager -> FasterWhisperTranscriptionWorker (transcriber.py)
  ├── UIManager -> ProgressWindow, LoadingWindow, ProcessingWindow
  ├── RecordingDialogManager -> RecordingDialog.qml (circular volume indicator)
  ├── TrayMenuManager -> Tray menu creation and updates
  ├── SettingsCoordinator -> Settings synchronization
  ├── WindowVisibilityCoordinator -> Recording dialog visibility management
  ├── GPUSetupManager -> GPU detection and CUDA library configuration
  ├── GlobalShortcuts (shortcuts.py) -> pynput keyboard listener
  ├── LockManager -> single-instance enforcement via lock file
  └── ClipboardManager -> copies transcription to clipboard
```

**Recent Refactoring** (Phase 7 - Feb 2025):
- Extracted 8 manager classes to separate orchestration from implementation
- main.py reduced from 1229 → 1026 lines (203 lines / 16.5% reduction)
- Improved separation of concerns, testability, and maintainability
- Recording logic simplified with helper methods (toggle_recording: 124 → 40 lines)

**Manager pattern** (`blaze/managers/`): AudioManager, TranscriptionManager, UIManager, LockManager, TrayMenuManager, SettingsCoordinator, WindowVisibilityCoordinator, and GPUSetupManager separate concerns from the main controller.

**Key design decisions**:
- All inter-component communication uses Qt signals/slots (thread-safe)
- Audio recorded at 16kHz directly (optimized for Whisper, no resampling needed)
- Audio processed entirely in memory (no temp files to disk)
- Global shortcuts use KDE kglobalaccel D-Bus integration; default is Alt+Space
- WhisperModelManager (`blaze/whisper_model_manager.py`) handles model download/deletion/GPU detection
- **GPUSetupManager** (`blaze/managers/gpu_setup_manager.py`) handles CUDA library detection, LD_LIBRARY_PATH configuration, and process restart for GPU acceleration
- Settings persisted via QSettings (`blaze/settings.py`)
- Constants (app version, sample rates, defaults) in `blaze/constants.py`
- **Centralized visibility control**: Dialog/window visibility managed through single-source-of-truth methods with recursion prevention
- **QML-Python bridges**: Bidirectional communication via SettingsBridge (settings sync) and DialogBridge/AudioBridge (state/actions)
- **Debounced persistence**: Position and size changes debounced (500ms) to prevent excessive disk writes

**UI windows** are separate classes: `KirigamiSettingsWindow` (QML-based), `ProgressWindow`, `LoadingWindow`, `ProcessingWindow`, `VolumeMeter`.

## UI Architecture

### Settings Window (Kirigami QML)
Settings window uses **Kirigami QML UI** (`blaze/kirigami_integration.py`):
- Modern KDE Plasma styling matching the desktop environment
- QML pages in `blaze/qml/pages/` (Models, Audio, Transcription, Shortcuts, About, **UI**)
- Python-QML bridge via `SettingsBridge` for bidirectional communication
- `ActionsBridge` for user actions (open URL, system settings, etc.)
- Display scaling support via `devicePixelRatio` detection
- Replaces old PyQt6 widget UI (removed in commit 0031ca5)

**UIPage Settings** (`blaze/qml/pages/UIPage.qml`):
- Recording dialog visibility, size, always-on-top controls
- Progress window visibility and always-on-top controls
- Bidirectional sync via `Connections` block listening to `settingChanged` signals

### Recording Dialog (QML Circular Window)
Recording indicator dialog (`blaze/recording_dialog_manager.py`, `blaze/qml/RecordingDialog.qml`):
- Circular frameless window with real-time volume visualization
- Features:
  - Volume-based radial gradient (green→yellow→red as volume increases)
  - Left-click: Toggle recording (250ms debounce vs double-click)
  - Double-click: Dismiss dialog
  - Right-click: Context menu (Start/Stop, Clipboard, Settings, Dismiss)
  - Middle-click: Open clipboard manager
  - Drag: Move window using Qt's `startSystemMove()`
  - Scroll wheel: Resize (100-500px range)
- Settings persistence: position, size, always-on-top, visibility
- **AudioBridge**: Exposes recording state, volume, transcription state to QML
- **DialogBridge**: Handles QML→Python actions (toggle recording, open clipboard, etc.)
- Position saves debounced (500ms after drag stops) to prevent excessive writes
- 300ms click-ignore delay after showing to prevent accidental interactions

## Known Issues & Ongoing Work

### Recording Dialog Settings Persistence (Active Work)

**Status**: Partially implemented, debugging in progress

**Working**:
- Settings UI in UIPage.qml displays and updates correctly
- Dialog size saves and restores
- Dialog visibility toggles work from settings UI

**Issues Being Fixed**:

1. **Window Position Persistence**:
   - **Problem**: Position not saving on drag (QML `xChanged`/`yChanged` signals don't fire from Python)
   - **Solution**: Use QML `onXChanged`/`onYChanged` handlers to call `dialogBridge.saveWindowPosition(x, y)`
   - **Implementation**: Added position debouncing (500ms timer) in QML, handler in Python
   - **Wayland Note**: Position restore may not work on Wayland due to compositor restrictions

2. **Always-On-Top Toggle**:
   - **Problem**: Dialog stays on top even when setting is disabled (Wayland compositor behavior)
   - **Root Cause**: `Qt.WindowType.Tool` windows always stay on top on Wayland
   - **Solution**: Switch to `Qt.WindowType.Window` for better flag control
   - **Status**: Implementation in progress

3. **Visibility Synchronization**:
   - **Problem**: Dialog visibility must sync between QML UI, Python code, and system tray menu
   - **Solution**: Centralized control via `set_recording_dialog_visibility(visible, source)` in main.py
   - **Features**:
     - Single source of truth for visibility state
     - `_updating_dialog_visibility` flag prevents recursive updates
     - Source tracking for debugging ("startup", "settings_ui", "tray_menu", etc.)
   - **Status**: Code written, testing in progress

4. **Dialog Shows on Startup When Disabled**:
   - **Problem**: QML `visible: true` causes brief flash before Python hides it
   - **Solution**: Change to `visible: false` in QML, let Python show it explicitly
   - **Status**: Fix implemented

5. **Window Border on First Show**:
   - **Problem**: Window flags set in `show()` instead of `initialize()`
   - **Solution**: Set flags during window creation, not on show
   - **Status**: Fix implemented

### Files Modified (Uncommitted):
- `blaze/main.py` - Centralized visibility control, recursion prevention
- `blaze/progress_window.py` - Always-on-top setting support
- `blaze/recording_dialog_manager.py` - Position save via QML handlers, window flag management
- `blaze/qml/RecordingDialog.qml` - Position tracking, click-ignore delay
- `blaze/qml/pages/UIPage.qml` - UI controls for dialog/window settings
- `blaze/settings.py` - New UI-related settings initialization

### New Files (Not Yet Integrated):
- `blaze/kwin_rules.py` - KWin window rules manager for Wayland always-on-top fallback (168 lines)
  - Uses `kwriteconfig6` to create window rules in `~/.config/kwinrulesrc`
  - Not yet integrated into main application

## Development Workflow

Use standard git branch workflow:
- `main` branch = stable production version
- Feature branches = development work
- Editable pipx install picks up changes immediately
- Switch branches and restart app to test different versions

```bash
# Work on feature
git checkout feature-branch
pkill syllablaze
syllablaze

# Test stable
git checkout main
pkill syllablaze
syllablaze
```

## Key Dependencies

PyQt6, faster-whisper (>=1.1.0), pyaudio, numpy, scipy, pynput, dbus-next, qasync, psutil, keyboard, hf_transfer

## CI

GitHub Actions (`.github/workflows/python-app.yml`): Python 3.10, flake8 lint, pytest. Runs on push/PR to main.
