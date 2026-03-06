# CLAUDE.md

Syllablaze: PyQt6 system tray app for Whisper-based speech-to-text on KDE Plasma.

## Critical Constraints

**NEVER:**
- Call `show()/hide()` directly on recording dialog → **Use `ApplicationState.set_recording_dialog_visible()`**
- Use `QTimer.singleShot(N, ...)` for Wayland window mapping → **Connect to `QWindow::visibilityChanged`**
- Write audio temp files → **Keep in memory (numpy arrays)**
- Skip KWin rules when changing window properties

**ALWAYS:**
- Use Qt signals/slots for inter-component communication
- Test on both X11 and Wayland when changing window management
- Debounce position/size persistence (500ms)

## Common Gotchas

- **Always-on-top toggle** requires restart on Wayland (compositor limitation)
- **Window position** cannot be restored on Wayland (compositor controls placement)
- Settings use two-level architecture: `popup_style` → derives → backend settings via `SettingsCoordinator`

## If You Get Stuck

Explore using: `blaze/main.py` (entry), `blaze/managers/` (coordinators), `blaze/settings.py` (QSettings wrapper)

## Git & Branch Discipline

- One working copy per repo — do NOT create a new top-level folder for each branch.
- Use branches inside the existing `archon` repo instead of cloning again for feature work.
- Long-lived branches:
  - `main` — latest development (PR target for contributors)
  - `stable` — recommended for day-to-day use and deployments
- Short-lived branches:
  - `feature/<short-description>` for new work
  - `fix/<short-description>` for bug fixes

### Agent branch handling

- The agent MUST only make changes against an explicitly specified branch.
- The caller MUST tell the agent which branch to use (e.g. `branch=feature/git-integration-cleanup`).
- If no branch is specified, the agent MUST refuse to modify code and instead reply:
  - That the branch was not provided.
  - That it cannot make changes until a branch name is given.
- The agent MUST NOT silently:
  - Switch branches,
  - Create new branches,
  - Or assume a default branch (like `main` or `stable`) when one is not specified.
- Once a branch is specified, the agent MUST stay on that branch for the duration of the task.

