# Syllablaze Known Issues & Bug Tracker

> **Last updated:** February 16, 2026
> **Current version:** 0.4 beta

---

## P0 â€” Blocks Core Functionality

### CUDA Backend Dropout After Recording Dialog Refactor
- **Symptom:** CUDA/GPU transcription stops working; falls back to CPU silently.
- **Trigger:** Refactor that merged two recording dialog methods/classes.
- **Root cause (suspected):** The merged code path no longer passes `device="cuda"` or equivalent flag to the transcription engine. The old path A (now removed) was the one that configured CUDA; surviving path B defaults to CPU.
- **Where to look:**
  - `blaze/main.py` â€” `ApplicationTrayIcon.toggle_recording()` and how it calls `TranscriptionManager`
  - `blaze/managers/transcription_manager.py` â€” `configure_optimal_settings()` and model loading
  - `blaze/settings.py` â€” `DEFAULT_DEVICE` is `'cpu'`; check if the setting is being read and passed through
  - `blaze/transcriber.py` â€” where `model.transcribe()` is called; verify device propagation
- **Fix approach:** Trace the call path from "user clicks record" â†’ model construction. Confirm `settings.get('device')` returns `'cuda'` and that value reaches `faster_whisper.WhisperModel(device=...)`.
- **Workaround:** Manually set device to `cuda` in settings and restart.

---

## P1 â€” Serious, Has Workaround

### Clipboard Integration Intermittent
- **Symptom:** Transcribed text sometimes doesn't appear in clipboard.
- **Status:** Mostly working as of latest testing session (Feb 16).
- **Where to look:** `blaze/clipboard_manager.py`
- **Notes:** May be related to Wayland clipboard behavior (clipboard clears when source window closes). Test on both X11 and Wayland.

### Window Rendering / Garbled Display
- **Symptom:** Recording/progress window occasionally renders garbled or fails to redraw.
- **Status:** Intermittent; observed during development sessions.
- **Where to look:** `blaze/window.py`, `blaze/progress_window.py`, `blaze/processing_window.py`
- **Possible causes:**
  - Qt widget not receiving paint events properly
  - Window shown before fully initialized
  - State transitions (RecordingState â†” ProcessingState) not cleaning up properly
- **Workaround:** Close and reopen the window.

---

## P2 â€” Annoying but Livable

### Mixed Naming Conventions (Manager vs Coordinator vs Orchestrator)
- **Symptom:** Confusion about which class is responsible for what.
- **Impact:** Makes refactoring riskier; harder for AI agents to reason about the codebase.
- **Fix:** See `orchestration_design.md` for proposed naming convention.

### `ApplicationTrayIcon` God-Class
- **Symptom:** `blaze/main.py` `ApplicationTrayIcon` is ~700 lines and handles tray UI, recording flow, settings, window lifecycle, and backend initialization.
- **Impact:** Any change to this class risks side effects in unrelated areas.
- **Fix:** Extract into orchestration layer (see `orchestration_design.md` migration plan).

### SVG Icon Not Yet in Repository
- **Symptom:** `resources/` still only contains `syllablaze.png`; the new SVG with named elements (status_indicator, waveform) exists only locally.
- **Fix:** Push `syllablaze.svg` to `resources/` and update icon loading in `main.py`.

---

## P3 â€” Nice to Have / Future

### No Type Hints or Static Analysis
- **Impact:** Refactoring bugs (like CUDA dropout) aren't caught until runtime.
- **Fix:** Add type hints incrementally; add `mypy` to CI.

### No Automated Tests for Recording Flow
- **Impact:** End-to-end recording â†’ transcription â†’ clipboard path has no test coverage.
- **Where:** `tests/` exists but only has `test_audio_processor.py`.
- **Fix:** Add integration test that exercises `start_recording â†’ stop_recording â†’ verify clipboard` with a mock audio source.

### Settings Not Reactive
- **Impact:** Changing settings (e.g., switching model or device) may require restart.
- **Fix:** `SettingsService` with `setting_changed` signal (see orchestration design).

---

## Resolved Issues

| Issue | Resolution | Date |
|---|---|---|
| Inkscape HSL/HSV sliders not updating gradient stops | Use RGB mode to commit changes; known Inkscape UI bug | Feb 16, 2026 |
| Gradient line not appearing in Inkscape | Press G (Gradient tool) then click object | Feb 16, 2026 |
| Donut mask for waveform area | Path â†’ Difference with mic shape on top of background rect | Feb 16, 2026 |
