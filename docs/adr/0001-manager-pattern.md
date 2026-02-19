# ADR-0001: Manager Pattern for Component Organization

**Status:** Accepted
**Date:** 2026-02-19
**Deciders:** Agent + Developer

## Context

The original `TrayRecorder` class in Syllablaze became a monolithic "god object" with too many responsibilities:

- Audio recording lifecycle management
- Whisper model loading and transcription
- Multiple UI windows (progress, loading, processing)
- Settings coordination
- Tray menu management
- GPU setup and CUDA detection
- Global keyboard shortcuts
- Single-instance locking

This created several problems:

- **Testing difficulty:** Impossible to unit test individual responsibilities in isolation
- **Code clarity:** ~800+ line class with unclear boundaries between concerns
- **Maintainability:** Changes to one feature risked breaking unrelated features
- **Agent collaboration:** AI agents struggled to understand the tangled dependencies
- **Reusability:** Functionality couldn't be reused outside the monolith

The codebase needed a clear organizational pattern that:
- Separated concerns with single responsibilities
- Enabled independent testing of components
- Facilitated agent-driven development with clear boundaries
- Maintained thread-safe communication via Qt signals/slots

## Decision

Extract responsibilities into **specialized Manager classes**, each with a single, well-defined purpose. The `SyllablazeOrchestrator` (renamed from `TrayRecorder`) acts as a coordinator, instantiating managers and wiring signal connections.

### Manager Classes Created

1. **AudioManager** (`blaze/managers/audio_manager.py`)
   - Responsibility: Recording lifecycle, PyAudio integration
   - Signals: `recording_started`, `recording_stopped`, `audio_data_ready`

2. **TranscriptionManager** (`blaze/managers/transcription_manager.py`)
   - Responsibility: FasterWhisperTranscriptionWorker coordination
   - Signals: `transcription_started`, `transcription_completed`, `transcription_failed`

3. **UIManager** (`blaze/managers/ui_manager.py`)
   - Responsibility: ProgressWindow, LoadingWindow, ProcessingWindow lifecycle
   - Signals: `window_shown`, `window_hidden`

4. **SettingsCoordinator** (`blaze/managers/settings_coordinator.py`)
   - Responsibility: Derives backend settings from high-level UI settings
   - Signals: `backend_settings_changed`

5. **WindowVisibilityCoordinator** (`blaze/managers/window_visibility_coordinator.py`)
   - Responsibility: Auto-show/hide recording dialog based on app state
   - Signals: None (listens to `ApplicationState` signals)

6. **TrayMenuManager** (`blaze/managers/tray_menu_manager.py`)
   - Responsibility: Tray menu creation, updates, state synchronization
   - Signals: `action_triggered`

7. **GPUSetupManager** (`blaze/managers/gpu_setup_manager.py`)
   - Responsibility: CUDA detection, LD_LIBRARY_PATH config, process restart
   - Signals: `gpu_setup_completed`

8. **LockManager** (`blaze/managers/lock_manager.py`)
   - Responsibility: Single-instance enforcement via lock file
   - Signals: None (raises exception if lock fails)

### Orchestrator Pattern

```python
class SyllablazeOrchestrator(QSystemTrayIcon):
    def __init__(self):
        # Instantiate managers
        self.audio_manager = AudioManager(settings)
        self.transcription_manager = TranscriptionManager(settings)
        self.ui_manager = UIManager(settings)
        # ... etc

        # Wire signal connections
        self._setup_connections()

    def _setup_connections(self):
        # Inter-manager communication via signals
        self.audio_manager.recording_stopped.connect(
            self.transcription_manager.start_transcription
        )
        self.transcription_manager.transcription_completed.connect(
            self.ui_manager.hide_progress
        )
```

### Communication Pattern

- **Managers never reference each other directly** (no tight coupling)
- **All communication via Qt signals/slots** (thread-safe, decoupled)
- **Orchestrator wires connections** during initialization
- **ApplicationState as single source of truth** for shared state

## Consequences

### Positive

- **Testability:** Each manager can be unit tested in isolation with mocks
- **Clarity:** Each file has ~100-300 lines with clear responsibility
- **Maintainability:** Changes localized to relevant manager
- **Agent-friendly:** AI agents easily locate code by responsibility
- **Extensibility:** New managers can be added without touching existing code
- **Thread safety:** Qt signals/slots handle cross-thread communication safely
- **Debugging:** Signal flow is traceable and easier to debug

### Negative

- **Indirection:** Following code execution requires tracing signal connections
- **Setup overhead:** Orchestrator `_setup_connections()` must wire all signals
- **Learning curve:** New contributors must understand manager pattern
- **Boilerplate:** Each manager requires similar initialization structure

### Neutral

- **File count:** Increased from 1 monolithic file to 8+ manager files
- **Import complexity:** More imports in orchestrator (but clearer dependencies)

## Alternatives Considered

### Alternative 1: Monolithic Orchestrator

- **Description:** Keep all logic in `TrayRecorder`, add helper methods
- **Pros:** Simple, no signal wiring needed, direct method calls
- **Cons:** Doesn't solve testability or maintainability problems
- **Reason for rejection:** Doesn't address core issues, continues technical debt

### Alternative 2: Microservices Architecture

- **Description:** Separate processes for audio, transcription, UI with IPC
- **Pros:** True isolation, could scale across machines
- **Cons:** Massive overkill, complex IPC, latency issues, debugging nightmare
- **Reason for rejection:** Unnecessary complexity for desktop application

### Alternative 3: Inheritance Hierarchy

- **Description:** Base `Manager` class with common functionality, managers inherit
- **Pros:** Code reuse for common patterns
- **Cons:** Managers have different needs, inheritance creates tight coupling
- **Reason for rejection:** Composition over inheritance principle; managers too diverse

### Alternative 4: Plugin System

- **Description:** Dynamically loaded plugins for each responsibility
- **Pros:** Ultimate flexibility, hot-reload capability
- **Cons:** Unnecessary complexity, harder debugging, no need for runtime changes
- **Reason for rejection:** Over-engineering for stable codebase with known components

## References

- **Code:** `blaze/main.py` (SyllablazeOrchestrator), `blaze/managers/` (all managers)
- **Documentation:** [Architecture Overview](../developer-guide/architecture.md)
- **Testing:** `tests/test_*_manager.py` (manager unit tests)
- **Related ADRs:** None (foundational decision)
- **External:** [Martin Fowler - Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)

---

**Implementation notes:**
- Managers follow naming convention: `<Responsibility>Manager`
- All managers in `blaze/managers/` directory
- Orchestrator in `blaze/main.py` (entry point)
- Signal connections documented in `_setup_connections()` method
- Add new managers to CLAUDE.md file map for agent reference
