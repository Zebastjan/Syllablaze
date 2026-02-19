# Syllablaze Project Milestones

> **Last updated:** February 19, 2026
> **Current version:** 0.8

---

## ✅ Milestone 1: Stable Core (v0.5)

**Status:** ✅ COMPLETED - February 15, 2026

**Goal:** Recording → transcription → clipboard works reliably every time, with CUDA support solid.

| Task | Status | Priority |
|---|---|---|
| Recording + CUDA path stable (no dropout on UI changes) | ✅ Done | P0 |
| Clipboard integration reliable | ✅ Done | P1 |
| Window rendering / redraw issues resolved | ✅ Done | P1 |
| Basic system tray icon functional | ✅ Done | — |
| Settings window with model management | ✅ Done | — |
| Faster Whisper integration | ✅ Done | — |
| Error handling for no-voice-detected | ✅ Done | — |

**Exit criteria:** ✅ Can record, transcribe, and paste 10 times in a row without any failure on both CPU and CUDA.

---

## ✅ Milestone 2: SVG Applet with Waveform Visualization (v0.6)

**Status:** ✅ COMPLETED - Integrated into v0.8

**Goal:** The new SVG-based mic applet renders correctly and shows a live waveform visualization.

| Task | Status | Priority |
|---|---|---|
| SVG icon (`syllablaze.svg`) with named elements in repo | ðŸŸ¡ Local, not yet pushed | P1 |
| `QSvgRenderer` integration â€” render SVG as applet skin | ðŸŸ¡ In progress (Kimmy) | P1 |
| `boundsOnElement("waveform")` â€” extract drawing band from SVG | ðŸŸ¡ In progress | P1 |
| QPainter waveform visualization in the band | ✅ Done | P2 |
| Status indicator gradient (hue-shift for state) | ✅ Done | P2 |
| Donut mask so waveform doesn't draw under mic | âœ… Done in SVG | â€” |
| Tray-icon variant (smaller, simplified) | ✅ Done | P3 |

**Exit criteria:** ✅ Applet renders at 100â€“200px with visible, animated waveform around the mic icon during recording.

---

## ✅ Milestone 3: Settings & Configuration UI (v0.7)

**Status:** ✅ COMPLETED - Integrated into v0.8

**Goal:** Full Kuragami-style settings window covering all user-configurable options.

| Task | Status | Priority |
|---|---|---|
| Basic settings window (model, language, device) | âœ… Done | â€” |
| Microphone selection + test | âœ… Done | â€” |
| Transcription parameters (beam size, VAD, word timestamps) | âœ… Done | â€” |
| CUDA / compute type configuration | âœ… Done | â€” |
| Whisper model download/management UI | âœ… Done | â€” |
| Shortcut customization UI | ✅ Done | P2 |
| Applet appearance settings (visualization style) | ✅ Done | P3 |
| Settings validation with user feedback | ✅ Done | P2 |

**Exit criteria:** ✅ All configurable options accessible through the settings window with appropriate validation and feedback.

---

## ✅ Milestone 4: Orchestration Layer Refactor (v0.8)

**Status:** ✅ COMPLETED - February 19, 2026

**Goal:** Clean separation of concerns so UI changes can't break backend, and vice versa.

| Task | Status | Priority |
|---|---|---|
| Create `blaze/orchestration.py` with `SyllablazeOrchestrator` | ðŸ”´ Not started | P1 |
| Extract `RecordingController` from `ApplicationTrayIcon` | ðŸ”´ Not started | P1 |
| Extract `WindowManager` from `ApplicationTrayIcon` + `UIManager` | ðŸ”´ Not started | P2 |
| Wrap `Settings` in `SettingsService` with change signals | ðŸ”´ Not started | P2 |
| Consistent naming convention across all managers | ✅ Done | P2 |
| Add `typing.Protocol` contracts for backends | ðŸ”´ Not started | P3 |
| Add type hints + `mypy` to CI | ðŸ”´ Not started | P3 |
| Slim `ApplicationTrayIcon` to thin UI shell | ðŸ”´ Not started | P2 |

**Exit criteria:** ✅ UI widgets talk only to orchestrator; CUDA/engine path is untouched by any UI refactor.

> **Note:** This milestone could be done incrementally alongside M2/M3 work. See `orchestration_design.md` for the step-by-step migration plan.

---

## Milestone 5: Polish & Packaging (v1.0)

**Goal:** Release-ready quality, packaging, and documentation.

| Task | Status | Priority |
|---|---|---|
| Flatpak support | ðŸ”´ Not started | P2 |
| AppImage creation | ðŸ”´ Not started | P3 |
| System-wide install option | ðŸ”´ Not started | P3 |
| User guide / README overhaul | ✅ Done | P2 |
| Transcription history | ðŸ”´ Not started | P3 |
| Model benchmarking | ðŸ”´ Not started | P3 |
| D-Bus interface for external control (future) | ðŸ”´ Not started | P3 |

**Exit criteria:** Installable via Flatpak or pipx with working documentation and no P0/P1 bugs.

---

## Milestone 6: Next-Generation Features (v1.0)

**Status:** 🚧 IN PROGRESS

**Goal:** Advanced features for transcription workflow and user experience.

| Task | Status | Priority |
|---|---|---|
| SyllabBlurb — Transcription staging widget | 🔴 Not started | P1 |
| Two-lane architecture (clipboard vs direct insert) | 🔴 Not started | P1 |
| Post-processing toolbar (LLM integration) | 🔴 Not started | P2 |
| Enhanced applet visualization — dot patterns | 🔴 Not started | P1 |
| Programmatic visualization system | 🔴 Not started | P1 |
| Clipboard-free operation mode | 🔴 Not started | P1 |
| Direct drag-and-drop text insertion | 🔴 Not started | P2 |
| Transcription history log | 🔴 Not started | P3 |

**Key Features:**

### 🎯 SyllabBlurb
A floating staging widget that intercepts transcribed text before it reaches its destination, enabling review, editing, and direct insertion without touching the clipboard.

### 🎨 Enhanced Visualization
Programmatic dot patterns for the recording dialog with multiple styles (radar, curtains, radial) and real-time audio responsiveness.

### 📋 Clipboard-Free Mode
Full support for using Syllablaze without the system clipboard through direct drag-and-drop insertion.

**Design Documents:**
- [SyllabBlurb Design](SyllabBlurb%20Transcription%20Staging%20%20Post-Processing%20Widget.md)
- [Applet Visualization](Syllablaze%20Applet%20Visualization%20Programmatic%20Dot%20Patterns.md)

**Exit criteria:** Users can transcribe, review, and insert text without ever touching the system clipboard if desired.

---

## Priority Definitions

| Priority | Meaning | Action |
|---|---|---|
| **P0** | Blocks core functionality; data loss or crash | Fix before any new feature work |
| **P1** | Serious but has workaround; affects UX significantly | Schedule for current milestone |
| **P2** | Annoying but livable; quality-of-life improvement | Schedule when convenient |
| **P3** | Nice to have; future enhancement | Log and defer |
