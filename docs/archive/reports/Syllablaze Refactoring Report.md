# Syllablaze Refactoring Report
**Date:** 2026-02-15 | **Repo:** PabloVitasso/Syllablaze (main branch)

***

## Executive Summary

Syllablaze is a Python + PyQt6 real-time audio transcription app using Faster Whisper. Prior refactoring rounds addressed naming conventions and function complexity (documented in `docs/refactoring_done/`), and extracted manager classes into `blaze/managers/`. However, significant structural issues remain: dead/duplicate code, mixed abstraction levels, missing interfaces, insufficient test coverage, and several files that still violate single-responsibility. This report provides both architectural guidance and concrete file-level action items for the next refactoring phase.

***

## 1. Dead and Duplicate Code

These are the highest-priority cleanup items because they create confusion for both humans and AI agents navigating the codebase.

### 1.1 `blaze/window.py` (359 lines) — Entirely Dead

`window.py` contains `WhisperWindow`, `RecordingDialog`, and `ModernFrame`. **No file in the entire codebase imports from it.** It appears to be the original windowed UI that was replaced by the system-tray approach in `main.py`. It also directly imports `AudioRecorder` and `WhisperTranscriber`, bypassing the manager layer.

**Action:** Delete `blaze/window.py` entirely. If any UI patterns from it are still wanted, extract them into proper components later.

### 1.2 `blaze/utils.py` vs `blaze/utils/__init__.py` — Duplicate

Both files define the identical `center_window()` function. The `blaze/utils.py` file (12 lines) is a flat module, while `blaze/utils/__init__.py` (12 lines) is the package init. Some files import from `blaze.utils` (which resolves to the package), but the standalone `blaze/utils.py` creates ambiguity.

**Action:** Delete `blaze/utils.py` (the flat file). Keep `blaze/utils/__init__.py` as the canonical location. Verify all imports resolve correctly.

### 1.3 `blaze/shortcuts.py` (71 lines) — Unused

`GlobalShortcuts` is defined but never imported or instantiated anywhere in the codebase.

**Action:** If keyboard shortcuts are a planned feature, move to a `blaze/integrations/` or `blaze/input/` module and wire it up. If not planned for v0.4, delete it and track in a backlog issue.

### 1.4 `blaze/clipboard_manager.py` (36 lines) — Unused

`ClipboardManager` class is defined but never imported. Clipboard operations in `main.py` use `QApplication.clipboard().setText()` directly.

**Action:** Either delete and keep using Qt clipboard directly, or wire `ClipboardManager` into the orchestrator as the single clipboard interface (preferred for testability).

### 1.5 `blaze/processing_window.py` (30 lines) — Unused

`ProcessingWindow` is defined but never imported anywhere.

**Action:** Delete. The `ProgressWindow` class already handles processing-mode display.

### 1.6 `tests/audio_manager.py` — Duplicate of `tests/test_audio_processor.py`

`tests/audio_manager.py` is a standalone test script (not pytest-compatible) that duplicates every test in `tests/test_audio_processor.py`. It uses `assert` statements and `if __name__ == "__main__"` rather than pytest fixtures.

**Action:** Delete `tests/audio_manager.py`. Keep only the pytest-compatible `tests/test_audio_processor.py`.

***

## 2. Architectural Issues

### 2.1 Two Whisper Model Managers

This is the single biggest structural smell in the codebase. There are **two** whisper model manager modules:

| File | Lines | Purpose |
|---|---|---|
| `blaze/whisper_model_manager.py` | 886 | UI widgets (`WhisperModelTableWidget`, `ModelDownloadDialog`), model registry, download threads, utility classes (`ModelPaths`, `ModelUtils`, `ModelRegistry`, `DialogUtils`, `DownloadManager`) |
| `blaze/utils/whisper_model_manager.py` | 522 | Core model operations (`WhisperModelManager` class): load, download, delete, query HuggingFace, detect CUDA/CTranslate2 |

These overlap significantly. `blaze/whisper_model_manager.py` has its own `ModelUtils.is_model_downloaded()` while `blaze/utils/whisper_model_manager.py` has `WhisperModelManager.is_model_downloaded()`. Both define model path logic. Both reference the same constants.

**Target decomposition:**

| New Module | Contents | Source |
|---|---|---|
| `blaze/models/registry.py` | `ModelRegistry`, `FASTER_WHISPER_MODELS` dict, model metadata | From `blaze/whisper_model_manager.py` |
| `blaze/models/paths.py` | `ModelPaths` utility class | From `blaze/whisper_model_manager.py` |
| `blaze/models/manager.py` | `WhisperModelManager` (load, download, delete, query HF) | From `blaze/utils/whisper_model_manager.py` |
| `blaze/models/download.py` | `ModelDownloadThread`, `DownloadManager`, progress tracking | From `blaze/whisper_model_manager.py` |
| `blaze/ui/model_table.py` | `WhisperModelTableWidget`, `ModelDownloadDialog` | From `blaze/whisper_model_manager.py` |
| `blaze/ui/dialogs.py` | `DialogUtils`, `confirm_download`, `confirm_delete` | From `blaze/whisper_model_manager.py` |

After this split, delete both original files.

### 2.2 `ApplicationTrayIcon` in `main.py` — Still Too Many Responsibilities

`main.py` is 716 lines containing:
- `ApplicationTrayIcon` class (~340 lines): tray icon setup, recording toggle logic, signal handling, progress window management, transcription result handling, tooltip updates, settings window management, shutdown/cleanup
- `check_dependencies()` function
- `main()` entry point
- `initialize_tray()` and helper functions (`_initialize_tray_ui`, `_initialize_audio_manager`, `_initialize_transcription_manager`, `_connect_signals`)
- Global state (`tray_recorder_instance`, `lock_manager`)

**Target decomposition:**

| New Module | Contents |
|---|---|
| `blaze/app.py` | `main()`, `setup_application_metadata()`, `check_dependencies()`, `cleanup_lock_file()`, application bootstrap |
| `blaze/tray_icon.py` | `ApplicationTrayIcon` (slimmed to: icon setup, menu creation, click handling, tooltip). Should delegate all business logic to the orchestrator |
| `blaze/orchestrator.py` | New class `SyllablazeOrchestrator`: owns recording state machine, coordinates audio_manager + transcription_manager + ui_manager, handles signal wiring |
| `blaze/startup.py` | `initialize_tray()` and its helpers — or fold into orchestrator's `initialize()` method |

The key principle: `ApplicationTrayIcon` should know about icons, menus, and clicks. It should **not** know about audio managers, transcription, or progress windows.

### 2.3 CUDA/Compute Backend Detection Scattered

CUDA/torch/CTranslate2 detection currently lives in:
- `blaze/managers/transcription_manager.py` lines 56-65 (`import torch; torch.cuda.is_available()`)
- `blaze/utils/whisper_model_manager.py` lines 289-330 (CTranslate2 catalog, CUDA compute type mapping)
- `blaze/settings.py` (validation of 'cuda' device)
- `blaze/settings_window.py` line 97 (hardcoded `['cpu', 'cuda']` combo items)
- `blaze/constants.py` (`DEFAULT_DEVICE = 'cpu'`)

**Action:** Create `blaze/compute/backend.py`:

```python
class ComputeBackend:
    """Detect and manage compute capabilities"""
    
    @staticmethod
    def detect_gpu() -> bool: ...
    
    @staticmethod  
    def get_optimal_settings() -> dict: ...
    
    @staticmethod
    def get_available_devices() -> list[str]: ...
    
    @staticmethod
    def get_compute_type_for_device(device: str) -> str: ...
```

All CUDA/torch/CTranslate2 imports should be isolated here. The rest of the codebase should call `ComputeBackend` methods instead of doing ad-hoc `import torch` checks.

***

## 3. File-by-File Action Items

### `blaze/main.py` (716 lines)
- [ ] Extract `ApplicationTrayIcon` to `blaze/tray_icon.py`
- [ ] Extract orchestration logic to `blaze/orchestrator.py`
- [ ] Move `main()` and bootstrap to `blaze/app.py`
- [ ] Remove `tray_recorder_instance` global; use proper dependency injection
- [ ] Remove duplicate `# Initialize basic state` comment (line 63-64)
- [ ] The `_recording_lock` uses a boolean flag (line 128) instead of a proper `threading.Lock` — replace with `threading.Lock` or `QMutex`
- [ ] `toggle_debug_window()` (line 536) references `self.debug_window` and `self.debug_action` which are never defined — dead method, delete

### `blaze/transcriber.py` (327 lines)
- [ ] `WhisperTranscriber.update_language()` (lines 196-230) iterates all top-level widgets and their children looking for QSystemTrayIcon objects to call `update_tooltip()` — this is a massive layer violation. The transcriber should emit a signal; the tray icon should listen.
- [ ] `FasterWhisperTranscriptionWorker` creates a new `Settings()` instance every time — should receive settings via constructor injection
- [ ] Move compute-type mapping logic out to `ComputeBackend`

### `blaze/recorder.py` (393 lines)
- [ ] `JackErrorFilter` class and stderr replacement (lines 20-42) is a global side effect at import time — isolate into a setup function called explicitly during initialization
- [ ] ALSA error suppression via ctypes (lines 70-88) is also a global side effect — same treatment
- [ ] `self._instance = self` (line 101) is a prevent-GC hack — investigate root cause instead of patching

### `blaze/whisper_model_manager.py` (886 lines)
- [ ] Split into 4-6 modules as described in §2.1
- [ ] `DialogUtils` class and standalone `confirm_download`/`confirm_delete`/`open_directory` functions are duplicates of each other — remove the standalone functions
- [ ] `get_model_info()` standalone function (line 192) duplicates `ModelRegistry` functionality

### `blaze/utils/whisper_model_manager.py` (522 lines)
- [ ] `load_model()` method (130 lines) does too many things: hf_transfer check, import faster_whisper, compute type mapping, CTranslate2 catalog attempt, standard/distil branching, fallback download — break into smaller methods
- [ ] `download_model()` method spawns a thread internally — should return a thread/future that the caller manages

### `blaze/settings.py` (130 lines)
- [ ] `get()` method is 60+ lines of if/elif chains — refactor to a validation registry pattern:
  ```python
  VALIDATORS = {
      'mic_index': validate_int,
      'language': validate_language,
      'beam_size': validate_range(1, 10),
      ...
  }
  ```
- [ ] Each `Settings()` instantiation creates a new `QSettings` object — consider making it a singleton or passing it around

### `blaze/settings_window.py` (318 lines)
- [ ] Imports `WhisperModelTableWidget` from `blaze.whisper_model_manager` — after split, import from `blaze/ui/model_table.py`
- [ ] Hardcodes device options `['cpu', 'cuda']` — should query `ComputeBackend.get_available_devices()`

### `blaze/managers/transcription_manager.py` (303 lines)
- [ ] `configure_optimal_settings()` does `import torch` inline — move to `ComputeBackend`
- [ ] `initialize()` method creates a `WhisperTranscriber` and connects signals but also does model-download checking — split initialization from validation

### `blaze/managers/audio_manager.py` (210 lines)
- [ ] `stop_recording()` calls `self.recorder._stop_recording()` (a private method) — `AudioRecorder` should expose a public `stop_recording()` method
- [ ] Timeout checks (lines 110, 140) use `time.time()` comparisons that only log warnings but don't actually timeout — either implement real timeouts or remove the misleading checks

### `blaze/managers/ui_manager.py` (143 lines)
- [ ] Reasonable size, but should be the single place that creates/manages windows — currently `ApplicationTrayIcon` creates `ProgressWindow` directly

### `blaze/managers/lock_manager.py` (157 lines)
- [ ] Good isolation. No changes needed.

### `blaze/audio_processor.py` (270 lines)
- [ ] Well-structured, good static methods. No immediate issues.
- [ ] `WHISPER_SAMPLE_RATE` is duplicated here and in `constants.py` — use single source

### `blaze/constants.py` (55 lines)
- [ ] Clean. Consider grouping constants into dataclasses or namespaced classes for better organization as the app grows.

### `blaze/ui/state_manager.py` (67 lines)
- [ ] Only defines `RecordingState` and `ProcessingState` — these are just state enums/classes. Fine as-is.

### `blaze/volume_meter.py` (97 lines)
- [ ] Custom Qt widget, well-scoped. No changes needed.

### `blaze/loading_window.py` (57 lines), `blaze/progress_window.py` (134 lines)
- [ ] Clean, focused UI components. No changes needed.

***

## 4. Test Coverage Gaps

Current test coverage is minimal: one pytest file (`test_audio_processor.py`) covering only `AudioProcessor`. The following areas have **zero test coverage**:

| Area | Suggested Test Module | Priority |
|---|---|---|
| Settings validation | `tests/test_settings.py` | High — Settings bugs cascade everywhere |
| AudioManager start/stop/signals | `tests/test_audio_manager.py` | High |
| TranscriptionManager initialization | `tests/test_transcription_manager.py` | Medium |
| WhisperModelManager (load, download, is_downloaded) | `tests/test_model_manager.py` | Medium |
| LockManager acquire/release | `tests/test_lock_manager.py` | Low — simple but important |
| Recording state machine (toggle logic) | `tests/test_recording_flow.py` | High — this is where race conditions live |

The existing `conftest.py` has good mock fixtures (`MockPyAudio`, `MockSettings`, `MockStream`) that should be reused. The CI pipeline (`.github/workflows/python-app.yml`) already runs pytest on push/PR, so adding tests will immediately provide regression protection.

**Quick wins:**
- Test `Settings.get()` validation for each setting type (5-10 tests, high value)
- Test `AudioManager.start_recording()` / `stop_recording()` with mocked recorder (catches the private-method-call bug)
- Test `LockManager.acquire_lock()` / `release_lock()` (trivial to write)

***

## 5. Proposed Target Directory Structure

```
blaze/
├── __init__.py
├── app.py                          # Entry point, main(), bootstrap
├── constants.py                    # App-wide constants
├── orchestrator.py                 # NEW: Central coordinator
│
├── audio/
│   ├── __init__.py
│   ├── processor.py                # ← audio_processor.py
│   └── recorder.py                 # ← recorder.py (cleaned up)
│
├── compute/
│   ├── __init__.py
│   └── backend.py                  # NEW: CUDA/CPU detection, compute type mapping
│
├── managers/
│   ├── __init__.py
│   ├── audio_manager.py            # (existing, cleaned)
│   ├── lock_manager.py             # (existing, unchanged)
│   └── transcription_manager.py    # (existing, CUDA bits removed)
│
├── models/
│   ├── __init__.py
│   ├── registry.py                 # Model metadata, FASTER_WHISPER_MODELS
│   ├── paths.py                    # ModelPaths utility
│   ├── manager.py                  # WhisperModelManager core logic
│   └── download.py                 # Download threads, progress tracking
│
├── transcription/
│   ├── __init__.py
│   └── transcriber.py              # ← transcriber.py (cleaned up)
│
├── settings/
│   ├── __init__.py
│   ├── store.py                    # ← settings.py (with validation registry)
│   └── validators.py               # NEW: Setting validation functions
│
├── ui/
│   ├── __init__.py
│   ├── tray_icon.py                # NEW: ApplicationTrayIcon (UI only)
│   ├── settings_window.py          # ← settings_window.py
│   ├── model_table.py              # NEW: WhisperModelTableWidget
│   ├── dialogs.py                  # NEW: DialogUtils, confirmations
│   ├── loading_window.py           # (existing)
│   ├── progress_window.py          # (existing)
│   ├── volume_meter.py             # ← volume_meter.py
│   └── state_manager.py            # (existing)
│
├── integrations/
│   ├── __init__.py
│   ├── clipboard.py                # ← clipboard_manager.py (if kept)
│   └── shortcuts.py                # ← shortcuts.py (if kept)
│
└── utils/
    ├── __init__.py                 # center_window() etc.
    └── (remove whisper_model_manager.py after split)

tests/
├── __init__.py
├── conftest.py
├── pytest.ini
├── test_audio_processor.py         # (existing)
├── test_settings.py                # NEW
├── test_audio_manager.py           # NEW
├── test_transcription_manager.py   # NEW
├── test_model_manager.py           # NEW
├── test_lock_manager.py            # NEW
└── test_recording_flow.py          # NEW
```

***

## 6. Additional Suggestions

### 6.1 install.py Improvements
- `install.py` (200+ lines) has a Popen call that reads from `process.stdout` after it's already been consumed in a while loop (line ~108 vs ~120) — this is a bug where the second read loop will never execute
- The spinner thread creates imports inside a function body (`import threading, time, itertools`) — move to top of file
- Consider splitting into `scripts/install.py` and keeping the project root cleaner

### 6.2 setup.py Is Auto-Generated
`setup.py` is written by `install.py` at install time with a hardcoded version `"0.3"` while `constants.py` says `"0.4 beta"`. Either:
- Remove dynamic setup.py generation and commit a proper `setup.py` / `pyproject.toml`
- Or at least read the version from `constants.py`

### 6.3 Documentation Cleanup
The `docs/` directory has ~30 refactoring documents. The completed ones are in `docs/refactoring_done/` but the active ones (`refactoring_04` through `refactoring_10`) should be reviewed — some may describe work that's already been done. Archive completed docs to `docs/refactoring_done/` to reduce noise.

### 6.4 Signal Naming Convention
Some signals use past tense (`recording_completed`), some use present continuous (`volume_changing`). Pick one convention and apply consistently. The existing convention of past-tense for completed events and present-continuous for ongoing updates (documented in `recorder.py`) is sensible — just enforce it everywhere.

### 6.5 Global Side Effects at Import Time
`recorder.py` replaces `sys.stderr` at module import time (line 42: `sys.stderr = JackErrorFilter(sys.stderr)`). This affects the entire Python process and will surprise anyone importing the module for testing. Move to an explicit `setup_audio_error_suppression()` function called during app initialization.

### 6.6 Consider pyproject.toml Migration
The project uses `setup.py` + `requirements.txt`. Modern Python packaging recommends `pyproject.toml`. This is low priority but would simplify the install story and eliminate the auto-generated setup.py issue.

***

## 7. Prioritized Refactoring Order

For maximum impact with minimum risk, execute in this order:

1. **Delete dead code** (§1): `window.py`, `processing_window.py`, `utils.py`, `shortcuts.py` (if unused), `clipboard_manager.py` (if unused), `tests/audio_manager.py` — zero behavior change, immediate clarity improvement
2. **Split the two whisper model managers** (§2.1) — this is the largest single confusion source
3. **Extract CUDA/compute detection** (§2.3) — small effort, eliminates scattered torch imports
4. **Break up main.py** (§2.2) — extract tray icon and orchestrator
5. **Clean up recorder.py side effects** (§6.5) — reduce import-time surprises
6. **Add priority tests** (§4) — Settings, AudioManager, LockManager
7. **Restructure into target directory layout** (§5) — do this last as it touches all imports