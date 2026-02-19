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

GitHub Actions (`.github/workflows/python-app.yml`): Python 3.10, flake8 lint, pytest, mkdocs build. Runs on push/PR to main. Deploys documentation to GitHub Pages on push to main.

---

## File Map (for AI Agents)

Use this map to quickly locate key components when working on features.

### Core Application
- `blaze/main.py` - Entry point, SyllablazeOrchestrator, qasync event loop
- `blaze/settings.py` - QSettings wrapper, validation, signal emission
- `blaze/application_state.py` - Single source of truth for app state
- `blaze/constants.py` - App version, sample rates, defaults

### Managers (`blaze/managers/`)
- `audio_manager.py` - Recording lifecycle, PyAudio integration
- `transcription_manager.py` - FasterWhisperTranscriptionWorker coordination
- `ui_manager.py` - ProgressWindow, LoadingWindow, ProcessingWindow
- `settings_coordinator.py` - Derives backend settings from popup_style
- `window_visibility_coordinator.py` - Auto-show/hide recording dialog
- `tray_menu_manager.py` - Tray menu creation, updates, state sync
- `gpu_setup_manager.py` - CUDA detection, LD_LIBRARY_PATH config
- `lock_manager.py` - Single-instance enforcement via lock file
- `window_settings_manager.py` - Window property persistence

### UI Components
- `kirigami_integration.py` - Settings window, SettingsBridge, ActionsBridge
- `recording_dialog_manager.py` - Recording dialog, RecordingDialogBridge
- `qml/SyllablazeSettings.qml` - Main settings window
- `qml/RecordingDialog.qml` - Circular waveform applet
- `qml/pages/*.qml` - Settings pages (Models, Audio, UI, Transcription, Shortcuts, About)

### Audio/Transcription
- `recorder.py` - AudioRecorder class, PyAudio wrapper
- `audio_processor.py` - Frame conversion, numpy integration
- `transcriber.py` - FasterWhisperTranscriptionWorker
- `whisper_model_manager.py` - Model download/deletion/verification

### Utilities
- `shortcuts.py` - GlobalShortcuts, pynput keyboard listener, KGlobalAccel D-Bus
- `clipboard_manager.py` - Persistent clipboard service, Wayland workarounds
- `kwin_rules.py` - KWin D-Bus window management
- `svg_renderer_bridge.py` - SVG element bounds extraction

### Documentation
- `CLAUDE.md` - Agent-focused architecture and constraints (this file)
- `README.md` - User-facing features and installation
- `CONTRIBUTING.md` - Contribution guidelines, PR process
- `docs/` - MkDocs documentation site
- `docs/adr/` - Architecture Decision Records
- `docs/developer-guide/` - Development setup, testing, patterns
- `docs/user-guide/` - Settings reference, features, troubleshooting

---

## Critical Constraints (for AI Agents)

**NEVER:**
- Call `show()/hide()` directly on recording dialog → **Use `ApplicationState.set_recording_dialog_visible()`**
- Use `QTimer.singleShot(N, ...)` to wait for window mapping on Wayland → **Connect to `QWindow::visibilityChanged`**
- Assume `settings.set()` emits signals programmatically → **Must manually trigger `SettingsCoordinator.on_setting_changed()`** if bypassing SettingsBridge
- Use `Qt.WindowType.Tool` for always-on-top on Wayland → **Use `Qt.WindowType.Window` + KWin rules**
- Write temp files for audio → **Keep all audio in memory (numpy arrays)**
- Skip KWin rules when changing window properties → **Always update both window flags AND KWin rules**
- Create documentation without updating `mkdocs.yml` nav → **Add to navigation config**
- Modify settings without reading CLAUDE.md Settings Architecture first → **Understand derivation logic**

**ALWAYS:**
- Use Qt signals/slots for inter-component communication (thread-safe)
- Test on both X11 and Wayland when changing window management (check `$XDG_SESSION_TYPE`)
- Debounce position/size persistence (500ms) to reduce disk writes
- Add logging for D-Bus operations (debugging Wayland issues)
- Update CLAUDE.md file map when adding new managers/modules
- Create ADR for significant architectural decisions (see `docs/adr/template.md`)
- Update `docs/user-guide/settings-reference.md` when adding settings
- Run `mkdocs build --strict` to verify documentation before committing

---

## Common Agent Tasks

### Add a new setting
1. Define in `Settings.__init__()` with default value
2. Add getter/setter with validation in `Settings` class
3. Expose via `SettingsBridge` as pyqtProperty if QML needs access
4. Add UI control to appropriate QML settings page (`blaze/qml/pages/`)
5. Handle in `SettingsCoordinator.on_setting_changed()` if backend derivation needed
6. Update `docs/user-guide/settings-reference.md` with new setting documentation
7. Add test in `tests/test_settings.py`
8. Update `mkdocs.yml` if creating new documentation page

**Example commit message:**
```
feat: add transcription timeout setting

Add configurable timeout for long transcriptions with default 300s.
Updated settings reference documentation and added unit tests.
```

### Add a new manager
1. Create `blaze/managers/new_manager.py` with class `NewManager`
2. Follow manager pattern: signals for communication, no direct dependencies
3. Instantiate in `SyllablazeOrchestrator.__init__()`
4. Wire signals in `SyllablazeOrchestrator._setup_connections()`
5. Add to CLAUDE.md file map (this file, Managers section)
6. Add to `docs/developer-guide/architecture.md` if architecturally significant
7. Create ADR if design decision warrants it (use `docs/adr/template.md`)
8. Add unit tests in `tests/test_new_manager.py`

**Example:**
```python
# blaze/managers/notification_manager.py
class NotificationManager(QObject):
    notification_sent = pyqtSignal(str)  # Signal when notification shown

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def send_notification(self, title, message):
        # Implementation
        self.notification_sent.emit(message)
```

### Debug Wayland window issue
1. Enable detailed logging for window operations:
   ```python
   logger.debug(f"Window flags: {window.windowFlags()}")
   logger.debug(f"Window visible: {window.isVisible()}")
   ```
2. Test on both X11 and Wayland:
   ```bash
   export XDG_SESSION_TYPE=x11  # Force X11
   syllablaze
   # Then test Wayland
   export XDG_SESSION_TYPE=wayland
   syllablaze
   ```
3. Check if Qt window flags behave differently: compare `window.windowFlags()` output
4. Try KWin D-Bus fallback: `kwin_rules.set_window_property()`
5. Document workaround in `docs/explanation/wayland-support.md`
6. Update CLAUDE.md Known Issues section if workaround unavailable
7. Add to troubleshooting guide if user-facing issue

### Create an Architecture Decision Record (ADR)
1. Copy template: `cp docs/adr/template.md docs/adr/XXXX-title.md`
2. Number sequentially (0001, 0002, ...) - check `docs/adr/README.md` for next number
3. Fill sections:
   - **Context:** What problem needs solving? What constraints exist?
   - **Decision:** What did we choose and how is it implemented?
   - **Consequences:** Positive, negative, and neutral effects
   - **Alternatives:** What else was considered and why rejected?
   - **References:** Links to code, docs, issues
4. Add to `docs/adr/README.md` index table
5. Add to `mkdocs.yml` navigation under ADRs section
6. Reference ADR from code comments where decision is implemented:
   ```python
   # Implementation of Settings Coordinator pattern (see ADR-0003)
   class SettingsCoordinator:
       ...
   ```
7. Link from related explanation docs (e.g., `docs/explanation/design-decisions.md`)
8. Commit with descriptive message:
   ```
   docs: add ADR-0004 for notification system

   Documents decision to use D-Bus notifications instead of Qt
   native notifications for better KDE Plasma integration.
   ```

### Update documentation
1. **User-facing change:** Update `docs/user-guide/` (features, settings-reference, troubleshooting)
2. **Developer change:** Update `docs/developer-guide/` (architecture, testing, patterns)
3. **Design decision:** Update `docs/explanation/` or create ADR
4. **Navigation:** Add new pages to `mkdocs.yml` nav section
5. **Verify build:** Run `mkdocs build --strict` (fails on warnings)
6. **Preview locally:** Run `mkdocs serve` and view at http://localhost:8000
7. **Commit:** Include documentation updates in same commit as code changes

**Documentation types (Divio framework):**
- **Tutorial (Getting Started):** Step-by-step guide for new users
- **How-To (User Guide):** Task-oriented recipes for specific goals
- **Reference (Settings Reference, API):** Technical descriptions, comprehensive lists
- **Explanation (Design Decisions, Wayland Support):** Understanding concepts and rationale

### Add a test
1. Locate appropriate test file in `tests/` or create new one
2. Use fixtures from `tests/conftest.py` (MockPyAudio, MockSettings, sample_audio_data)
3. Add pytest marker if categorizing:
   ```python
   @pytest.mark.audio
   def test_audio_recording():
       ...
   ```
4. Test both success and failure cases
5. Add docstring explaining what test verifies
6. Run test: `pytest tests/test_new_feature.py -v`
7. Update `docs/developer-guide/testing.md` if new test pattern or scenario
8. Ensure CI passes: `pytest && flake8 . --max-line-length=127`
