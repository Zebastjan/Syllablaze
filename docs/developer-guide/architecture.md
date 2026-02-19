# Architecture Overview

High-level overview of Syllablaze's architecture. For detailed design rationale, see [Design Decisions](../explanation/design-decisions.md).

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  Tray Icon │  │   Settings   │  │ Recording Dialog  │   │
│  │            │  │   (QML)      │  │     (QML)         │   │
│  └────────────┘  └──────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              SyllablazeOrchestrator (Coordinator)            │
│                   (Qt Signal/Slot Wiring)                    │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Audio     │  │Transcription │  │      UI      │
│   Manager    │  │   Manager    │  │   Manager    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Settings   │  │   Window     │  │     Tray     │
│ Coordinator  │  │  Visibility  │  │     Menu     │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│     GPU      │  │     Lock     │  │   Clipboard  │
│    Setup     │  │   Manager    │  │   Manager    │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Core Components

### Entry Point: `blaze/main.py`

- Creates Qt application
- Initializes `SyllablazeOrchestrator`
- Sets up D-Bus service (`SyllaDBusService`)
- Starts qasync event loop

### Orchestrator: `SyllablazeOrchestrator`

**Responsibility:** Coordinate managers via Qt signals/slots

**Pattern:** Manager pattern with signal-based communication

**Key methods:**
- `__init__()` - Instantiate all managers
- `_setup_connections()` - Wire signal connections between managers
- Signal handlers for tray menu actions

**See:** [ADR-0001: Manager Pattern](../adr/0001-manager-pattern.md)

## Manager Layer

Each manager has single responsibility:

### AudioManager
**File:** `blaze/managers/audio_manager.py`
**Responsibility:** Recording lifecycle, PyAudio integration
**Signals:** `recording_started`, `recording_stopped`, `audio_data_ready`

### TranscriptionManager
**File:** `blaze/managers/transcription_manager.py`
**Responsibility:** Whisper transcription worker coordination
**Signals:** `transcription_started`, `transcription_completed`, `transcription_failed`

### UIManager
**File:** `blaze/managers/ui_manager.py`
**Responsibility:** Progress/Loading/Processing window lifecycle
**Signals:** `window_shown`, `window_hidden`

### SettingsCoordinator
**File:** `blaze/managers/settings_coordinator.py`
**Responsibility:** Derive backend settings from high-level UI settings
**Signals:** `backend_settings_changed`
**See:** [ADR-0003: Settings Coordinator](../adr/0003-settings-coordinator.md)

### WindowVisibilityCoordinator
**File:** `blaze/managers/window_visibility_coordinator.py`
**Responsibility:** Auto-show/hide recording dialog based on app state
**Listens to:** `ApplicationState` signals

### TrayMenuManager
**File:** `blaze/managers/tray_menu_manager.py`
**Responsibility:** Tray menu creation, updates, state sync
**Signals:** `action_triggered`

### GPUSetupManager
**File:** `blaze/managers/gpu_setup_manager.py`
**Responsibility:** CUDA detection, LD_LIBRARY_PATH config
**Signals:** `gpu_setup_completed`

### LockManager
**File:** `blaze/managers/lock_manager.py`
**Responsibility:** Single-instance enforcement via lock file
**Raises:** Exception if lock acquisition fails

## Data Flow

### Recording Flow

```
User presses Alt+Space
  ↓
GlobalShortcuts emits toggle_recording signal
  ↓
Orchestrator._on_toggle_recording()
  ↓
ApplicationState.start_recording()
  ↓
AudioManager starts PyAudio stream
  ↓
AudioRecorder captures frames → numpy array
  ↓
AudioManager.recording_stopped emitted
  ↓
TranscriptionManager.start_transcription()
  ↓
FasterWhisperTranscriptionWorker (QThread)
  ↓
TranscriptionManager.transcription_completed emitted
  ↓
ClipboardManager.copy_text()
  ↓
User pastes with Ctrl+V
```

### Settings Change Flow

```
User changes setting in QML UI
  ↓
SettingsBridge.set(key, value)
  ↓
Settings.set() validates and writes to QSettings
  ↓
SettingsBridge.settingChanged signal
  ↓
SettingsCoordinator.on_setting_changed()
  ↓
Derive backend settings (if high-level setting)
  ↓
Components react to backend setting changes
```

**See:** [Settings Architecture](../explanation/settings-architecture.md)

## UI Architecture

### QML Components

**Settings Window:** `blaze/qml/SyllablazeSettings.qml`
- Kirigami ApplicationWindow
- Page navigation (Models, Audio, Transcription, Shortcuts, UI, About)
- Python-QML bridge via `SettingsBridge`

**Recording Dialog:** `blaze/qml/RecordingDialog.qml`
- Circular frameless window
- Canvas-based radial waveform visualization
- Python-QML bridge via `RecordingDialogBridge`

**See:** [ADR-0002: QML Kirigami UI](../adr/0002-qml-kirigami-ui.md)

### QtWidgets Components

**Traditional Windows:** `ProgressWindow`, `LoadingWindow`, `ProcessingWindow`
- Simple QtWidgets dialogs
- No Kirigami (overkill for progress bars)

## Key Patterns

### Signal-Based Communication

**Rule:** Managers never reference each other directly

**Implementation:** Orchestrator wires signals in `_setup_connections()`

**Example:**
```python
self.audio_manager.recording_stopped.connect(
    self.transcription_manager.start_transcription
)
```

### Single Source of Truth: ApplicationState

**File:** `blaze/application_state.py`

**Properties:**
- `is_recording` (bool)
- `is_transcribing` (bool)
- `recording_dialog_visible` (bool)

**Critical:** Never call `show()/hide()` directly - use `ApplicationState.set_recording_dialog_visible()`

### Python-QML Bridges

**Pattern:** QObject with pyqtSignal/pyqtSlot/pyqtProperty

**Examples:**
- `SettingsBridge` - Settings access from QML
- `RecordingDialogBridge` - State and actions for recording dialog
- `ActionsBridge` - User actions (open URL, system settings)
- `SvgRendererBridge` - SVG element bounds extraction

## Threading Model

### Main Thread
- Qt event loop
- UI updates
- Signal/slot connections

### Worker Threads
- `FasterWhisperTranscriptionWorker` (QThread) - Whisper inference
- `GlobalShortcuts` (pynput) - Keyboard listener

**Rule:** Cross-thread communication via Qt signals (thread-safe)

## Dependency Management

### Runtime Dependencies
- PyQt6, faster-whisper, pyaudio, numpy, scipy, pynput
- dbus-next (D-Bus integration)
- qasync (async/await in Qt)

### Optional Dependencies
- CUDA/cuDNN (GPU acceleration)
- Kirigami (bundled with KDE Frameworks)

## File Organization

```
blaze/
├── main.py                    # Entry point
├── settings.py                # QSettings wrapper
├── application_state.py       # Single source of truth
├── constants.py               # App version, defaults
├── managers/                  # Manager pattern components
│   ├── audio_manager.py
│   ├── transcription_manager.py
│   └── ...
├── qml/                       # QML UI components
│   ├── SyllablazeSettings.qml
│   ├── RecordingDialog.qml
│   └── pages/
├── recorder.py                # AudioRecorder (PyAudio)
├── transcriber.py             # FasterWhisperWorker
├── whisper_model_manager.py   # Model download/delete
├── shortcuts.py               # GlobalShortcuts (pynput)
├── clipboard_manager.py       # Clipboard persistence
└── kwin_rules.py              # KWin D-Bus integration
```

## Testing Strategy

- **Unit tests:** Mock-based, no hardware dependencies
- **Mocks:** `MockPyAudio`, `MockSettings` in `tests/conftest.py`
- **Fixtures:** Sample audio data, settings instances
- **Markers:** `@pytest.mark.audio`, `@pytest.mark.ui`, etc.

**See:** [Testing Guide](testing.md)

## Platform-Specific Code

### KDE Plasma / KWin
- `kwin_rules.py` - D-Bus window management
- `shortcuts.py` - KGlobalAccel integration

### Wayland
- `clipboard_manager.py` - Persistent clipboard service
- Window position saving disabled (compositor controls)

**See:** [Wayland Support](../explanation/wayland-support.md)

---

**Related Documentation:**
- [Design Decisions](../explanation/design-decisions.md) - Why we built it this way
- [ADRs](../adr/README.md) - Architecture Decision Records
- [Patterns & Pitfalls](patterns-and-pitfalls.md) - Best practices
