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
