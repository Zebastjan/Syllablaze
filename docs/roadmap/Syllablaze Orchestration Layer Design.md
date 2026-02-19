# Syllablaze Orchestration Layer Design

> **Status:** Proposal â€” February 2026
> **Purpose:** Consolidate and clarify the coordination/orchestration classes to prevent cross-cutting bugs (e.g., UI refactor breaking CUDA path) and establish consistent naming.

---

## 1. Current State

Today the codebase has several "manager" / "coordinator" classes scattered across modules:

| Class | File | Role |
|---|---|---|
| `ApplicationTrayIcon` | `blaze/main.py` | Top-level app controller; owns managers, menus, recording flow, settings window, progress window |
| `UIManager` | `blaze/managers/ui_manager.py` | Centralized UI helpers (window management, notifications) |
| `AudioManager` | `blaze/managers/audio_manager.py` | Wraps `AudioRecorder`; owns recording signals |
| `TranscriptionManager` | `blaze/managers/transcription_manager.py` | Wraps `WhisperTranscriber`; owns model/language config |
| `UIState` / `RecordingState` / `ProcessingState` | `blaze/ui/state_manager.py` | State-pattern classes for the recording/processing UI |
| `Settings` | `blaze/settings.py` | QSettings wrapper with validation |
| `ClipboardManager` | `blaze/clipboard_manager.py` | Clipboard operations |
| `LockManager` | `blaze/managers/lock_manager.py` | Single-instance lock file |

### Problems

1. **`ApplicationTrayIcon` is doing too much.** It is simultaneously the system-tray widget *and* the top-level orchestrator. Recording flow, settings wiring, CUDA/model init, and window lifecycle all live here. A UI-only refactor (e.g., changing the recording dialog) can accidentally sever the backend path because the same class owns both.

2. **Mixed naming conventions.** We have "Manager," "State," "Settings," and no "Orchestrator" or "Coordinator" â€” despite conceptually wanting an orchestration layer.

3. **No single entry point for "what can the UI call?"** Widgets sometimes talk to `AudioManager` directly, sometimes to `ApplicationTrayIcon`, sometimes to `Settings`.

---

## 2. Proposed Architecture

### 2.1 File: `blaze/orchestration.py`

All orchestration classes live in one module so developers know: *"this is the central hub."*

```
blaze/orchestration.py
    â”œâ”€â”€ SyllablazeOrchestrator    (top-level conductor)
    â”œâ”€â”€ RecordingController       (recording lifecycle)
    â”œâ”€â”€ SettingsService            (config read/write/notify)
    â””â”€â”€ WindowManager              (window lifecycle)
```

### 2.2 Class Responsibilities

#### `SyllablazeOrchestrator`
- **The one class the UI talks to.** All public methods on this class form the "API contract."
- Owns instances of `RecordingController`, `SettingsService`, `WindowManager`.
- Owns `AudioManager` and `TranscriptionManager` (backend).
- Exposes high-level actions:

```python
class SyllablazeOrchestrator(QObject):
    # --- Signals (UI subscribes to these) ---
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_ready = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    # --- Public API (UI calls these) ---
    def start_recording(self) -> bool: ...
    def stop_recording(self) -> bool: ...
    def toggle_recording(self) -> None: ...
    def update_settings(self, key: str, value: Any) -> None: ...
    def get_setting(self, key: str, default: Any = None) -> Any: ...
    def open_settings_window(self) -> None: ...
    def close_settings_window(self) -> None: ...
    def shutdown(self) -> None: ...
```

#### `RecordingController`
- Manages the record â†’ stop â†’ transcribe â†’ clipboard pipeline.
- Talks to `AudioManager` and `TranscriptionManager`.
- Does **not** touch any UI widgets directly; emits signals only.

```python
class RecordingController(QObject):
    volume_update = pyqtSignal(float)
    transcription_progress = pyqtSignal(str, int)  # message, percent
    transcription_complete = pyqtSignal(str)        # result text
    recording_error = pyqtSignal(str)

    def start(self, settings: Settings) -> bool: ...
    def stop(self) -> bool: ...
    def is_active(self) -> bool: ...
```

#### `SettingsService`
- Wraps the existing `Settings` class.
- Adds a `setting_changed` signal so the orchestrator (and backend) can react to config changes without polling.
- Single source of truth for "what device, what model, what compute type."

```python
class SettingsService(QObject):
    setting_changed = pyqtSignal(str, object)  # key, new_value

    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def get_device(self) -> str: ...    # 'cpu' or 'cuda'
    def get_model(self) -> str: ...     # e.g. 'tiny', 'base'
```

#### `WindowManager`
- Creates, shows, hides, and destroys windows (ProgressWindow, SettingsWindow, LoadingWindow, future AppletWindow).
- Absorbs the window-lifecycle code currently in `ApplicationTrayIcon` and `UIManager`.

```python
class WindowManager(QObject):
    def show_progress(self, title: str) -> ProgressWindow: ...
    def show_settings(self) -> SettingsWindow: ...
    def show_loading(self) -> LoadingWindow: ...
    def close_all(self) -> None: ...
```

### 2.3 What `ApplicationTrayIcon` becomes

After refactor, `ApplicationTrayIcon` is a *thin shell*:
- Creates the tray icon and context menu.
- Holds one `SyllablazeOrchestrator` instance.
- Menu actions call `self.orchestrator.toggle_recording()`, `self.orchestrator.open_settings_window()`, etc.
- Subscribes to orchestrator signals to update icon/tooltip.

```python
class ApplicationTrayIcon(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.orchestrator = SyllablazeOrchestrator()
        self.orchestrator.recording_started.connect(self._show_recording_icon)
        self.orchestrator.recording_stopped.connect(self._show_normal_icon)
        self.orchestrator.error_occurred.connect(self._show_error_notification)
        self.setup_menu()
```

---

## 3. API Contract Enforcement

Python doesn't have compile-time interfaces, but we can get close:

### 3.1 Use `typing.Protocol` for swappable components

```python
from typing import Protocol, Any

class AudioBackend(Protocol):
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
    def get_volume(self) -> float: ...

class TranscriptionBackend(Protocol):
    def transcribe(self, audio_data) -> str: ...
    def load_model(self, model_name: str, device: str, compute_type: str) -> None: ...
```

### 3.2 Type hints everywhere + `mypy` / `pyright`

Add to CI (`.github/workflows/python-app.yml`):

```yaml
- name: Type check
  run: mypy blaze/ --ignore-missing-imports
```

### 3.3 Underscore convention

- Public API: no underscore prefix â†’ safe for UI to call.
- Internal: single underscore prefix â†’ not part of the contract.

---

## 4. Migration Plan

This can be done incrementally without breaking the app:

| Step | What | Risk |
|---|---|---|
| 1 | Create `blaze/orchestration.py` with `SyllablazeOrchestrator` as a thin wrapper that delegates to existing managers | Low â€” no behavior change |
| 2 | Route `ApplicationTrayIcon` actions through orchestrator instead of directly calling managers | Low â€” same logic, different call path |
| 3 | Extract `RecordingController` from `ApplicationTrayIcon.toggle_recording()` and related methods | Medium â€” test recording flow carefully |
| 4 | Extract `WindowManager` from `ApplicationTrayIcon` and `UIManager` | Medium â€” test window lifecycle |
| 5 | Wrap `Settings` in `SettingsService` with change signals | Low |
| 6 | Add type hints and `Protocol` definitions | Low |
| 7 | Slim down `ApplicationTrayIcon` to thin shell | Low after steps 2-5 |

**Rule:** After each step, recording + transcription + clipboard must still work end-to-end before proceeding.

---

## 5. Key Principle

> **UI widgets talk only to `SyllablazeOrchestrator`. Only `SyllablazeOrchestrator` (and its sub-controllers) talk to the backend.**

This single rule would have prevented the CUDA dropout caused by the recording dialog refactor: the dialog would only call `orchestrator.stop_recording()`, and the CUDA/device logic would live entirely inside `RecordingController` â†’ `TranscriptionManager`, untouched by any UI change.
