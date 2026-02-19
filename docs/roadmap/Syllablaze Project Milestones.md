# Syllablaze Project Milestones

> **Last updated:** February 16, 2026
> **Current version:** 0.4 beta

---

## Milestone 1: Stable Core (v0.5)

**Goal:** Recording â†’ transcription â†’ clipboard works reliably every time, with CUDA support solid.

| Task | Status | Priority |
|---|---|---|
| Recording + CUDA path stable (no dropout on UI changes) | ðŸ”´ Broken | P0 |
| Clipboard integration reliable | ðŸŸ¡ Mostly working | P1 |
| Window rendering / redraw issues resolved | ðŸŸ¡ Intermittent | P1 |
| Basic system tray icon functional | âœ… Done | â€” |
| Settings window with model management | âœ… Done | â€” |
| Faster Whisper integration | âœ… Done | â€” |
| Error handling for no-voice-detected | âœ… Done | â€” |

**Exit criteria:** Can record, transcribe, and paste 10 times in a row without any failure on both CPU and CUDA.

---

## Milestone 2: SVG Applet with Waveform Visualization (v0.6)

**Goal:** The new SVG-based mic applet renders correctly and shows a live waveform visualization.

| Task | Status | Priority |
|---|---|---|
| SVG icon (`syllablaze.svg`) with named elements in repo | ðŸŸ¡ Local, not yet pushed | P1 |
| `QSvgRenderer` integration â€” render SVG as applet skin | ðŸŸ¡ In progress (Kimmy) | P1 |
| `boundsOnElement("waveform")` â€” extract drawing band from SVG | ðŸŸ¡ In progress | P1 |
| QPainter waveform visualization in the band | ðŸ”´ Not started | P2 |
| Status indicator gradient (hue-shift for state) | ðŸŸ¡ Designed in Inkscape | P2 |
| Donut mask so waveform doesn't draw under mic | âœ… Done in SVG | â€” |
| Tray-icon variant (smaller, simplified) | ðŸ”´ Not started | P3 |

**Exit criteria:** Applet renders at 100â€“200px with visible, animated waveform around the mic icon during recording.

---

## Milestone 3: Settings & Configuration UI (v0.7)

**Goal:** Full Kuragami-style settings window covering all user-configurable options.

| Task | Status | Priority |
|---|---|---|
| Basic settings window (model, language, device) | âœ… Done | â€” |
| Microphone selection + test | âœ… Done | â€” |
| Transcription parameters (beam size, VAD, word timestamps) | âœ… Done | â€” |
| CUDA / compute type configuration | âœ… Done | â€” |
| Whisper model download/management UI | âœ… Done | â€” |
| Shortcut customization UI | ðŸ”´ Not started | P2 |
| Applet appearance settings (visualization style) | ðŸ”´ Not started | P3 |
| Settings validation with user feedback | ðŸŸ¡ Partial | P2 |

**Exit criteria:** All configurable options accessible through the settings window with appropriate validation and feedback.

---

## Milestone 4: Orchestration Layer Refactor (v0.8)

**Goal:** Clean separation of concerns so UI changes can't break backend, and vice versa.

| Task | Status | Priority |
|---|---|---|
| Create `blaze/orchestration.py` with `SyllablazeOrchestrator` | ðŸ”´ Not started | P1 |
| Extract `RecordingController` from `ApplicationTrayIcon` | ðŸ”´ Not started | P1 |
| Extract `WindowManager` from `ApplicationTrayIcon` + `UIManager` | ðŸ”´ Not started | P2 |
| Wrap `Settings` in `SettingsService` with change signals | ðŸ”´ Not started | P2 |
| Consistent naming convention across all managers | ðŸ”´ Not started | P2 |
| Add `typing.Protocol` contracts for backends | ðŸ”´ Not started | P3 |
| Add type hints + `mypy` to CI | ðŸ”´ Not started | P3 |
| Slim `ApplicationTrayIcon` to thin UI shell | ðŸ”´ Not started | P2 |

**Exit criteria:** UI widgets talk only to orchestrator; CUDA/engine path is untouched by any UI refactor.

> **Note:** This milestone could be done incrementally alongside M2/M3 work. See `orchestration_design.md` for the step-by-step migration plan.

---

## Milestone 5: Polish & Packaging (v1.0)

**Goal:** Release-ready quality, packaging, and documentation.

| Task | Status | Priority |
|---|---|---|
| Flatpak support | ðŸ”´ Not started | P2 |
| AppImage creation | ðŸ”´ Not started | P3 |
| System-wide install option | ðŸ”´ Not started | P3 |
| User guide / README overhaul | ðŸŸ¡ Partial | P2 |
| Transcription history | ðŸ”´ Not started | P3 |
| Model benchmarking | ðŸ”´ Not started | P3 |
| D-Bus interface for external control (future) | ðŸ”´ Not started | P3 |

**Exit criteria:** Installable via Flatpak or pipx with working documentation and no P0/P1 bugs.

---

## Priority Definitions

| Priority | Meaning | Action |
|---|---|---|
| **P0** | Blocks core functionality; data loss or crash | Fix before any new feature work |
| **P1** | Serious but has workaround; affects UX significantly | Schedule for current milestone |
| **P2** | Annoying but livable; quality-of-life improvement | Schedule when convenient |
| **P3** | Nice to have; future enhancement | Log and defer |
