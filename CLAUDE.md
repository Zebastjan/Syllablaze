# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Syllablaze is a PyQt6 system tray application for real-time speech-to-text transcription using OpenAI's Whisper (via faster-whisper). It records audio, transcribes it, and copies the result to clipboard. Targets KDE Plasma on Wayland/X11 Linux desktops. Installed as a user-level package via pipx.

## Current Development Status

**Active Development Areas** (as of Feb 2026):
- Always-on-top toggle requires restart to take effect (minor, deferred)
- Window position persistence on Wayland (compositor prevents it)

## Build and Run Commands

```bash
# Install (user-level via pipx)
python3 install.py

# Run directly during development
python3 -m blaze.main

# Dev update: copies to pipx install dir, restarts app
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
# ruff check blaze/ --fix  # optional
```

## Architecture

**Entry point**: `blaze/main.py` — `main()` creates the Qt application, initializes `SyllablazeOrchestrator` (the main controller), sets up D-Bus service (`SyllaDBusService`), and starts a qasync event loop.

**Core flow**:
```
SyllablazeOrchestrator (main.py) — orchestrator / QSystemTrayIcon
  ├── AudioManager -> AudioRecorder (recorder.py) -> PyAudio microphone input
  ├── TranscriptionManager -> FasterWhisperTranscriptionWorker (transcriber.py)
  ├── UIManager -> ProgressWindow, LoadingWindow, ProcessingWindow
  ├── RecordingDialogManager -> RecordingDialog.qml (circular volume indicator)
  ├── TrayMenuManager -> Tray menu creation and updates
  ├── SettingsCoordinator -> Derives backend settings from popup_style; syncs components
  ├── WindowVisibilityCoordinator -> Recording dialog auto-show/hide
  ├── GPUSetupManager -> GPU detection and CUDA library configuration
  ├── GlobalShortcuts (shortcuts.py) -> pynput keyboard listener
  ├── LockManager -> single-instance enforcement via lock file
  └── ClipboardManager -> copies transcription to clipboard
```

**Manager pattern** (`blaze/managers/`): AudioManager, TranscriptionManager, UIManager, LockManager, TrayMenuManager, SettingsCoordinator, WindowVisibilityCoordinator, GPUSetupManager.

**Key design decisions**:
- All inter-component communication uses Qt signals/slots (thread-safe)
- Audio recorded at 16kHz directly (optimized for Whisper, no resampling needed)
- Audio processed entirely in memory (no temp files to disk)
- Global shortcuts use KDE kglobalaccel D-Bus integration; default is Alt+Space
- WhisperModelManager (`blaze/whisper_model_manager.py`) handles model download/deletion/GPU detection
- **GPUSetupManager** handles CUDA library detection, LD_LIBRARY_PATH configuration, and process restart for GPU acceleration
- Settings persisted via QSettings (`blaze/settings.py`)
- Constants (app version, sample rates, defaults) in `blaze/constants.py`
- **ApplicationState** (`blaze/application_state.py`) is the single source of truth for recording/transcription/dialog state
- **Centralized visibility control**: all dialog visibility changes go through `ApplicationState.set_recording_dialog_visible()` — never call `show()/hide()` directly
- **QML-Python bridges**: `SettingsBridge` (settings + svgPath), `RecordingDialogBridge` (state/actions), `SvgRendererBridge` (SVG element bounds)
- **Debounced persistence**: position and size changes debounced (500ms) to prevent excessive disk writes
- **Post-show window properties on Wayland**: Never use `QTimer.singleShot(N, ...)` to wait for a window to be mapped. Instead connect to `QWindow::visibilityChanged` and disconnect after the first non-Hidden call. This is deterministic; arbitrary delays are a race condition.

**UI windows**: `KirigamiSettingsWindow` (QML-based), `ProgressWindow`, `LoadingWindow`, `ProcessingWindow`, `VolumeMeter`.

## Settings Architecture

Two high-level settings drive recording indicator behavior:

| Setting | Type | Default | Values |
|---|---|---|---|
| `popup_style` | str | `"applet"` | `"none"` / `"traditional"` / `"applet"` |
| `applet_autohide` | bool | `True` | relevant when `popup_style == "applet"` |

`SettingsCoordinator._apply_popup_style()` derives backend settings:

| popup_style | applet_autohide | show_progress_window | show_recording_dialog | applet_mode |
|---|---|---|---|---|
| none | — | False | False | off |
| traditional | — | True | False | off |
| applet | True | False | True | popup |
| applet | False | False | True | persistent |

The old backend settings (`show_recording_dialog`, `show_progress_window`, `applet_mode`) are kept — `SettingsCoordinator` writes them as derived values. `WindowVisibilityCoordinator` continues reading `applet_mode` unchanged.

## UI Architecture

### Settings Window (Kirigami QML)
Settings window uses **Kirigami QML UI** (`blaze/kirigami_integration.py`):
- Modern KDE Plasma styling matching the desktop environment
- QML pages in `blaze/qml/pages/` (Models, Audio, Transcription, Shortcuts, About, UI)
- Python-QML bridge via `SettingsBridge` for bidirectional communication
- `ActionsBridge` for user actions (open URL, system settings, etc.)
- Display scaling support via `devicePixelRatio` detection

**UIPage** (`blaze/qml/pages/UIPage.qml`):
- Visual 3-card radio selector: **None / Traditional / Applet**
- Each card has a QML-drawn preview (None: em-dash; Traditional: mini progress bar; Applet: real SVG)
- Conditional sub-options appear below selected card:
  - Applet: auto-hide toggle, dialog size spinbox, always-on-top switch
  - Traditional: always-on-top switch
- `SettingsBridge.svgPath` pyqtProperty exposes the SVG file path for the Applet card image

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
- Position saves debounced (500ms after drag stops)
- 300ms click-ignore delay after showing to prevent accidental interactions

### Popup / Visibility Mode
- `applet_mode=popup`: dialog auto-shows when recording starts, auto-hides 500ms after transcription
- `applet_mode=persistent`: dialog always visible
- `applet_mode=off`: dialog never shown automatically
- `WindowVisibilityCoordinator.connect_to_app_state()` wires up the auto-show/hide signals

## Settings Change Flow

```
QML settingsBridge.set(key, value)
  → Settings.set(key, value)            [validation + QSettings write]
  → SettingsBridge.settingChanged signal
  → SettingsCoordinator.on_setting_changed(key, value)
  → component update (visibility, always-on-top, derived settings, etc.)
```

## Known Issues

- **Always-on-top toggle**: requires restart or toggle off/on to take effect (Wayland compositor behavior)
- **Window position on Wayland**: compositor controls placement; restore may not work

## Development Workflow

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
