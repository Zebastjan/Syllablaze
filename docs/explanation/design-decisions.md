# Design Decisions

This document consolidates key design decisions in Syllablaze, explaining the rationale behind major architectural choices. For detailed decision records with alternatives and consequences, see [Architecture Decision Records (ADRs)](../adr/README.md).

## Core Principles

### Privacy First

**Decision:** All audio processing happens in-memory; no temporary files written to disk.

**Rationale:**
- Speech data is highly sensitive personal information
- Temp files could persist after crashes or be recovered by forensics
- In-memory processing is faster (no disk I/O)
- Simplifies cleanup (audio automatically cleared when variables deallocated)

**Implementation:**
- Audio captured directly into NumPy arrays (16kHz, int16)
- Arrays passed to Whisper model without intermediate storage
- Transcription result copied to clipboard then discarded

**Trade-off:** Limited by available RAM for very long recordings (mitigated by practical recording length limits).

**Reference:** `blaze/recorder.py:AudioRecorder`, `blaze/audio_processor.py`

---

### Direct 16kHz Recording

**Decision:** Record audio at 16kHz directly instead of device native rate with resampling.

**Rationale:**
- Whisper models expect 16kHz input
- Recording at 16kHz avoids resampling step (lower CPU usage)
- Lower sample rate = smaller in-memory buffers = better privacy
- 16kHz is sufficient for speech (human speech frequencies <8kHz per Nyquist)

**Implementation:**
- PyAudio configured with `rate=16000` parameter
- Settings provide "Device Native" option for compatibility (resamples afterward)
- Default is "Whisper (16 kHz)" mode

**Trade-off:** Some microphones may not support 16kHz natively (PyAudio handles resampling internally if needed).

**Reference:** `blaze/constants.py:WHISPER_SAMPLE_RATE`, `blaze/recorder.py`

---

### Manager Pattern

**Decision:** Extract responsibilities into specialized Manager classes coordinated by Orchestrator.

**Rationale:**
- Original monolithic `TrayRecorder` class had 800+ lines with tangled concerns
- Impossible to unit test individual features
- AI agents struggled with unclear component boundaries
- Changes to one feature risked breaking unrelated features

**Implementation:**
- 8+ manager classes, each with single responsibility (AudioManager, TranscriptionManager, UIManager, etc.)
- `SyllablazeOrchestrator` wires signal connections between managers
- No direct manager-to-manager references (loose coupling)
- All communication via Qt signals/slots (thread-safe)

**Trade-off:** More files and indirection, but significantly better testability and maintainability.

**Reference:** [ADR-0001: Manager Pattern](../adr/0001-manager-pattern.md)

---

### QML UI with Kirigami

**Decision:** Use QML with Kirigami framework for settings window and recording dialog.

**Rationale:**
- QtWidgets didn't match KDE Plasma's modern styling
- Kirigami provides native Breeze theme integration
- Declarative QML is more concise than manual QtWidgets layouts
- Better high-DPI support and responsive layouts
- Syllablaze targets KDE Plasma specifically

**Implementation:**
- Settings window: Kirigami `ApplicationWindow` with page navigation
- Recording dialog: QML `Window` with Canvas-based visualization
- Python-QML bridges: `SettingsBridge`, `RecordingDialogBridge`, `ActionsBridge`
- Traditional progress window remains QtWidgets (no Kirigami benefit)

**Trade-off:** Requires developers to know both Python and QML; QML debugging is harder.

**Reference:** [ADR-0002: QML Kirigami UI](../adr/0002-qml-kirigami-ui.md)

---

### Settings Coordinator

**Decision:** Derive backend settings from high-level user settings via SettingsCoordinator.

**Rationale:**
- Users shouldn't see implementation details (`show_recording_dialog`, `applet_mode`)
- Simple UI choice (None/Traditional/Applet) maps to multiple backend settings
- Prevents contradictory backend states (e.g., both progress window and dialog enabled)
- Centralizes derivation logic for testing and maintenance

**Implementation:**
- User-facing: `popup_style` + `applet_autohide` (high-level)
- Backend: `show_progress_window`, `show_recording_dialog`, `applet_mode` (derived)
- SettingsCoordinator listens to high-level changes and sets backend values

**Trade-off:** Additional indirection, but much simpler UX and clearer architecture.

**Reference:** [ADR-0003: Settings Coordinator](../adr/0003-settings-coordinator.md)

---

## UI/UX Decisions

### Centralized Visibility Control

**Decision:** All recording dialog visibility changes go through `ApplicationState.set_recording_dialog_visible()`.

**Rationale:**
- Direct `show()/hide()` calls create race conditions and inconsistent state
- ApplicationState is single source of truth for dialog visibility
- Enables auto-show/hide coordination (popup mode)
- Prevents duplicate show() calls or show-during-hide races

**Implementation:**
- `ApplicationState.recording_dialog_visible` property (boolean)
- `set_recording_dialog_visible(visible, source)` method emits `recording_dialog_visibility_changed` signal
- `WindowVisibilityCoordinator` listens to signal and manages actual window show/hide
- Components **never** call `recording_dialog.show()` or `recording_dialog.hide()` directly

**Enforcement:** Documented in CLAUDE.md "Critical Constraints" for AI agents.

**Reference:** `blaze/application_state.py`, `blaze/managers/window_visibility_coordinator.py`

---

### Debounced Persistence

**Decision:** Debounce position and size changes (500ms delay) before writing to settings.

**Rationale:**
- Window drag generates dozens of position updates per second
- Writing to QSettings on every update causes excessive disk I/O
- SSD wear concern for frequent writes
- User experience unchanged (persistence happens after drag stops)

**Implementation:**
- `QTimer.singleShot(500, self._save_position)` in position change handler
- Cancel pending save timer if new position change arrives
- Only writes once 500ms after last change

**Trade-off:** Position not saved if app crashes during 500ms window (acceptable rare case).

**Reference:** `blaze/recording_dialog_manager.py`

---

### Click-Ignore Delay

**Decision:** Ignore clicks for 300ms after recording dialog is shown.

**Rationale:**
- When dialog auto-shows on recording start, user may have shortcut key still pressed
- Accidental clicks can toggle recording off immediately
- Brief ignore window prevents frustrating false triggers

**Implementation:**
- `self._click_ignore_until = QDateTime.currentMSecsSinceEpoch() + 300`
- Click handlers check `if now < self._click_ignore_until: return`

**Trade-off:** 300ms delay before dialog is interactive (acceptable, user is focused on speaking).

**Reference:** `blaze/qml/RecordingDialog.qml`

---

## Platform Integration

### KWin Window Management

**Decision:** Use KWin D-Bus API for window properties (always-on-top, on-all-desktops) on Wayland.

**Rationale:**
- Qt6 removed `setOnAllDesktops()` method
- Wayland doesn't allow applications to set window properties directly
- KWin provides D-Bus scripting API for compositor-controlled properties
- KWin rules persist across application restarts

**Implementation:**
- `kwin_rules.py` module with D-Bus integration
- `set_window_on_all_desktops(window_id, enabled)` for immediate effect
- `create_or_update_kwin_rule(on_all_desktops=value)` for persistence
- Fallback to Qt window flags on X11

**Trade-off:** KDE Plasma specific; won't work on GNOME/Sway. Acceptable given target audience.

**Reference:** `blaze/kwin_rules.py`, [Wayland Support](wayland-support.md)

---

### pynput for Global Shortcuts

**Decision:** Use pynput keyboard listener for global shortcuts instead of X11-only libraries.

**Rationale:**
- Original `keyboard` library only worked on X11
- pynput supports both X11 and Wayland
- KDE KGlobalAccel D-Bus API used as primary method on Wayland
- pynput provides fallback for other desktop environments

**Implementation:**
- Primary: KGlobalAccel D-Bus registration (Wayland + X11 on KDE)
- Fallback: pynput keyboard listener (other DEs)
- Settings allow custom shortcut configuration

**Trade-off:** pynput requires accessibility permissions on some systems.

**Reference:** `blaze/shortcuts.py`

---

## Performance Decisions

### faster-whisper Backend

**Decision:** Use faster-whisper library instead of OpenAI's official whisper implementation.

**Rationale:**
- faster-whisper uses CTranslate2 (optimized inference engine)
- 2-4x faster transcription with same accuracy
- Lower memory usage via quantization (int8 support)
- GPU acceleration via CUDA without torch dependency bloat

**Implementation:**
- `FasterWhisperTranscriptionWorker` in separate thread
- WhisperModelManager downloads from Hugging Face Hub
- Supports compute types: float32, float16 (GPU), int8 (CPU)

**Trade-off:** Slightly more complex setup (CTranslate2 dependency), but significant performance gain.

**Reference:** `blaze/transcriber.py`, `blaze/whisper_model_manager.py`

---

### GPU Detection and Setup

**Decision:** Automatic CUDA library detection with LD_LIBRARY_PATH configuration.

**Rationale:**
- Many users have NVIDIA GPUs but don't configure CUDA paths
- Manually setting LD_LIBRARY_PATH is error-prone
- Automatic detection reduces support burden

**Implementation:**
- `GPUSetupManager` searches common CUDA library locations
- Configures LD_LIBRARY_PATH automatically
- Restarts application process to apply environment changes
- Falls back to CPU if CUDA not found

**Trade-off:** Application restart required for GPU activation (acceptable one-time setup).

**Reference:** `blaze/managers/gpu_setup_manager.py`

---

## Development Workflow Decisions

### pipx Installation

**Decision:** Distribute via pipx instead of distribution packages or Flatpak.

**Rationale:**
- pipx installs in isolated virtualenv (no system Python pollution)
- User-level installation (no sudo required)
- Easy to develop: `pipx install .` in repo directory
- Native system integration (no Flatpak sandbox issues)

**Implementation:**
- `install.py` wrapper script runs `pipx install .`
- `dev-update.sh` copies to pipx install directory for live testing

**Trade-off:** Requires users to install pipx first; not in distribution repos (yet).

**Reference:** `install.py`, `blaze/dev-update.sh`

---

### Agent-Driven Development

**Decision:** Embrace AI-assisted development with comprehensive agent documentation.

**Rationale:**
- Claude Code is effective for refactoring and feature implementation
- Agents need clear architecture documentation and constraints
- CLAUDE.md provides file map, critical patterns, common tasks
- ADRs document design rationale for agent context

**Implementation:**
- CLAUDE.md with file map, constraints, common agent tasks
- Architecture Decision Records (ADRs) for major decisions
- Memory files in `.claude/` directory for pattern documentation
- Detailed inline comments for complex Qt/Wayland workarounds

**Trade-off:** More documentation maintenance, but significantly faster development velocity.

**Reference:** [CLAUDE.md](../../CLAUDE.md), [ADRs](../adr/README.md)

---

## Testing Decisions

### Mock-Based Unit Tests

**Decision:** Use pytest with extensive mocks (MockPyAudio, MockSettings) instead of integration tests.

**Rationale:**
- Audio hardware access unreliable in CI environments
- Unit tests run fast and deterministically
- Mocks allow testing edge cases (device failures, model errors)

**Implementation:**
- `tests/conftest.py` provides shared fixtures and mocks
- `MockPyAudio` simulates audio device behavior
- `MockSettings` isolates tests from real QSettings

**Trade-off:** Mocks may not catch real hardware issues; manual testing still required.

**Reference:** `tests/conftest.py`, [Testing Guide](../developer-guide/testing.md)

---

## Future-Proofing Decisions

### ApplicationState as Single Source of Truth

**Decision:** Centralize recording/transcription/dialog state in ApplicationState class.

**Rationale:**
- Prevents state synchronization issues between components
- Makes state transitions explicit and traceable
- Enables future features (undo, state machine visualization)

**Implementation:**
- `ApplicationState` with properties for `is_recording`, `is_transcribing`, `recording_dialog_visible`
- Components read state from ApplicationState, never maintain local state
- State changes emit signals for component coordination

**Reference:** `blaze/application_state.py`

---

### Extensible Settings Architecture

**Decision:** Settings stored in QSettings with validation and type conversion layer.

**Rationale:**
- QSettings handles platform-specific storage automatically
- Validation prevents invalid settings (e.g., beam_size > 10)
- Type conversion handles string-to-bool and int edge cases
- Future: Could add settings migration for backward compatibility

**Implementation:**
- `Settings` class wraps QSettings with `get(key, default)` and `set(key, value)`
- Validation in setters (e.g., `set_beam_size()` rejects values outside 1-10)
- Boolean/int conversion handles QSettings string storage quirks

**Reference:** `blaze/settings.py`

---

## Related Documentation

- **[Architecture Decision Records](../adr/README.md)** - Detailed ADRs with alternatives and consequences
- **[Architecture Overview](../developer-guide/architecture.md)** - High-level system design
- **[Patterns & Pitfalls](../developer-guide/patterns-and-pitfalls.md)** - Qt/PyQt6 best practices
- **[Wayland Support](wayland-support.md)** - Wayland-specific design decisions
- **[Settings Architecture](settings-architecture.md)** - Settings derivation detailed explanation
