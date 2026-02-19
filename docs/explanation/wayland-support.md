# Wayland Support

Syllablaze runs on both X11 and Wayland, but Wayland's security-focused design creates challenges for desktop applications. This document explains Wayland-specific behaviors, workarounds, and limitations.

## What is Wayland?

Wayland is a modern display protocol replacing the aging X11 (X Window System). Key differences:

| Feature | X11 | Wayland |
|---------|-----|---------|
| **Window positioning** | Apps control | Compositor controls |
| **Global input capture** | Allowed | Restricted |
| **Screen capture** | Direct access | Portal API required |
| **Window properties** | App sets directly | Compositor enforces |
| **Security model** | Permissive | Restrictive |

**Wayland philosophy:** Applications request capabilities; the compositor decides whether to grant them. This improves security but reduces application control.

---

## Detecting X11 vs Wayland

```bash
echo $XDG_SESSION_TYPE
# Output: "x11" or "wayland"
```

Syllablaze automatically adapts behavior based on session type.

---

## Wayland-Specific Challenges

### 1. Window Position Persistence

**Issue:** Applications cannot programmatically set window positions on Wayland.

**X11 behavior:**
```python
window.move(saved_x, saved_y)  # Works on X11
```

**Wayland behavior:**
- `window.move()` is ignored (no error, just no effect)
- Compositor decides initial window placement based on its own rules
- User can drag window, but position doesn't persist

**Syllablaze workaround:**
- **Recording dialog:** Position saving **disabled** on Wayland
- `recording_dialog_x` and `recording_dialog_y` settings ignored on Wayland
- Compositor places window (usually near cursor or center of screen)
- User can drag dialog to preferred position, but won't persist across sessions

**Status:** Known limitation, no workaround. Wayland design decision for security (prevents apps from positioning windows over password dialogs, etc.).

**Reference:** `blaze/recording_dialog_manager.py:_restore_position_and_size()`

---

### 2. Always-On-Top Behavior

**Issue:** Qt window flags for "always on top" may not take effect immediately on Wayland.

**X11 behavior:**
```python
window.setWindowFlags(window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
window.show()  # Immediately on top
```

**Wayland behavior:**
- Window flags set, but compositor applies them on **next window creation**
- Changing flags on existing window may not take effect until window is re-created
- Behavior varies by compositor (KWin, Mutter, Sway)

**Syllablaze workaround - Dual approach:**

**Approach 1: KWin Rules (preferred on KDE):**
```python
# blaze/kwin_rules.py
def create_or_update_kwin_rule(on_all_desktops=None, keep_above=None):
    # Creates persistent KWin rule for Syllablaze recording dialog
    # Rule persists across app restarts
```

**Approach 2: Window flags (fallback):**
```python
# Set flags during initialization
flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
if always_on_top:
    flags |= Qt.WindowType.WindowStaysOnTopHint
window.setWindowFlags(flags)
```

**Known issue:** Toggling always-on-top setting may require:
- **Option 1:** Restart application
- **Option 2:** Toggle setting OFF, close dialog, toggle ON, reopen dialog

**Status:** Partial workaround. KWin rules work reliably; other compositors vary.

**Reference:**
- `blaze/kwin_rules.py`
- [Troubleshooting: Always-on-top requires restart](../getting-started/troubleshooting.md#always-on-top-requires-restart)

---

### 3. Show on All Desktops

**Issue:** Qt6 removed `setOnAllDesktops()` method; Wayland doesn't allow apps to set this directly.

**X11 (Qt5) behavior:**
```python
window.setOnAllDesktops(True)  # Method removed in Qt6
```

**Wayland behavior:**
- Qt6 removed method entirely (Wayland can't support it)
- Apps must request compositor to set property via D-Bus

**Syllablaze workaround - KWin D-Bus API:**

**Immediate effect (for running window):**
```python
# blaze/kwin_rules.py
def set_window_on_all_desktops(window_id, enabled):
    # Uses KWin D-Bus scripting API
    # Applies property immediately to window
```

**Persistence (for future windows):**
```python
def create_or_update_kwin_rule(on_all_desktops=True):
    # Creates KWin rule that persists across app restarts
```

**Implementation:**
```python
# When setting changes
if wayland_session:
    window_id = get_kwin_window_id(window)
    kwin_rules.set_window_on_all_desktops(window_id, True)  # Immediate
    kwin_rules.create_or_update_kwin_rule(on_all_desktops=True)  # Persistence
```

**Status:** **Works reliably on KDE Plasma/KWin**. Other compositors (Mutter, Sway) don't expose equivalent D-Bus API.

**Reference:** `blaze/kwin_rules.py:set_window_on_all_desktops()`

---

### 4. Global Keyboard Shortcuts

**Issue:** Wayland restricts global input capture for security.

**X11 behavior:**
- Apps can use `XGrabKey()` to register global shortcuts
- Libraries like `python-keyboard` use X11 APIs

**Wayland behavior:**
- No direct global input access (prevents keyloggers)
- Desktop environments provide D-Bus registration APIs
- Requires desktop-specific integration

**Syllablaze solution - Dual approach:**

**Primary: KDE KGlobalAccel (Wayland + X11 on KDE):**
```python
# blaze/shortcuts.py
def register_kglobalaccel_shortcut():
    # Uses org.kde.kglobalaccel5 D-Bus service
    # Native KDE Plasma integration
    # Works on both X11 and Wayland
```

**Fallback: pynput (other desktop environments):**
```python
# Uses pynput keyboard listener
# Requires accessibility permissions on some systems
# Works on X11 and Wayland (via evdev)
```

**Status:** **Works reliably.** KGlobalAccel on KDE, pynput elsewhere.

**Reference:** `blaze/shortcuts.py:GlobalShortcuts`

---

### 5. Clipboard Persistence

**Issue:** On Wayland, clipboard data is lost when the source window is hidden/closed.

**X11 behavior:**
- Clipboard data persists in X server
- Source app can close, data remains available

**Wayland behavior:**
- Clipboard data **owned by source app**
- If source app hides window or exits, data may be lost
- Compositor doesn't maintain clipboard buffer

**Syllablaze problem:**
- Recording dialog auto-hides after transcription (popup mode)
- Clipboard data would be lost on hide

**Syllablaze workaround - Persistent clipboard service:**

```python
# blaze/clipboard_manager.py
class ClipboardManager:
    def __init__(self):
        self.clipboard = QApplication.clipboard()
        self.clipboard_data = None  # Persistent storage

    def copy_text(self, text):
        # Store in instance variable (persistent)
        self.clipboard_data = text
        # Also copy to system clipboard
        self.clipboard.setText(text)

    # Keep clipboard_manager instance alive for entire app lifetime
    # Even when recording dialog is hidden
```

**Key insight:** ClipboardManager instance lives in SyllablazeOrchestrator (never destroyed), so clipboard data persists even when recording dialog is hidden.

**Status:** **Fixed in v0.5**. Clipboard works reliably on Wayland.

**Reference:**
- `blaze/clipboard_manager.py`
    - [GitHub Issue: Clipboard not working on Wayland](https://github.com/Zebastjan/Syllablaze/issues/XX)

---

### 6. Window Identification

**Issue:** Identifying windows by title/class for KWin rules is unreliable on Wayland.

**X11 behavior:**
- `WM_CLASS` property is standard
- Window title is reliable

**Wayland behavior:**
- App ID may differ from window class
- Window title can change dynamically
- No standardized window identification

**Syllablaze approach:**

**Use multiple identifiers:**
```python
def get_kwin_window_id(window):
    title = window.windowTitle()  # "Syllablaze Recording"
    app_id = "syllablaze"  # XDG app ID
    class_name = "syllablaze"  # Qt application name

    # KWin D-Bus API searches by multiple properties
    # Increases reliability of window matching
```

**KWin rule uses wmclass + title pattern:**
```ini
# ~/.config/kwinrulesrc
[Syllablaze Recording Dialog]
wmclass=syllablaze
wmclassmatch=1
title=.*Recording.*
titlematch=3  # Substring match
```

**Status:** Works reliably when window title is stable.

**Reference:** `blaze/kwin_rules.py:get_kwin_window_id()`

---

## Window Mapping Detection

**Issue:** Need to detect when window is fully mapped before applying properties.

**Wrong approach (race condition):**
```python
window.show()
QTimer.singleShot(100, apply_kwin_properties)  # Arbitrary delay
```

**Correct approach (deterministic):**
```python
def on_visibility_changed(visibility):
    if visibility != QWindow.Visibility.Hidden:
        # Window is now mapped
        apply_kwin_properties()
        # Disconnect after first call
        window.visibilityChanged.disconnect(on_visibility_changed)

window.visibilityChanged.connect(on_visibility_changed)
window.show()
```

**Rationale:**
- Arbitrary timers create race conditions (window may not be mapped yet)
- `visibilityChanged` signal fires when window is actually mapped
- Deterministic, works on both slow and fast systems

**Reference:** CLAUDE.md "Critical Constraints" section

---

## Testing on Wayland

### Switch Between X11 and Wayland

**Method 1: Log out and select session type:**
1. Log out of KDE Plasma
2. At login screen, click session selector (gear icon)
3. Choose "Plasma (X11)" or "Plasma (Wayland)"
4. Log in

**Method 2: Start nested Wayland session (testing):**
```bash
# Start nested Wayland compositor for testing
export XDG_SESSION_TYPE=wayland
export QT_QPA_PLATFORM=wayland
syllablaze
```

**Verify session type:**
```bash
echo $XDG_SESSION_TYPE
loginctl show-session $(loginctl | grep $USER | awk '{print $1}') -p Type
```

---

## Wayland Debugging Tips

### Enable Qt Wayland logging

```bash
export QT_LOGGING_RULES="qt.qpa.wayland*=true"
syllablaze
```

### Check KWin D-Bus availability

```bash
qdbus org.kde.KWin /KWin org.kde.KWin.supportInformation
```

### List KWin windows

```bash
qdbus org.kde.KWin /KWin org.kde.KWin.queryWindowInfo
```

### Inspect KWin rules

```bash
cat ~/.config/kwinrulesrc
```

### Monitor D-Bus traffic

```bash
dbus-monitor --session "destination=org.kde.KWin"
```

---

## Compositor Compatibility

| Compositor | Desktop Environment | Always-On-Top | On All Desktops | Global Shortcuts | Status |
|------------|---------------------|---------------|-----------------|------------------|--------|
| **KWin** | KDE Plasma | ✅ (via D-Bus) | ✅ (via D-Bus) | ✅ (KGlobalAccel) | **Full support** |
| Mutter | GNOME | ⚠️ (flags only) | ❌ | ⚠️ (pynput) | Partial support |
| Sway | Sway (tiling) | ⚠️ (flags only) | ❌ | ⚠️ (pynput) | Partial support |
| Weston | Reference | ❌ | ❌ | ❌ | Minimal support |

**Legend:**
- ✅ Full support (native API)
- ⚠️ Partial support (fallback method)
- ❌ Not supported

**Syllablaze is optimized for KDE Plasma.** Other compositors work with reduced functionality.

---

## Known Limitations (Wayland)

**No workaround available:**
1. **Window position persistence** - Compositor controls placement
2. **On all desktops (non-KDE)** - No standard Wayland protocol

**Workarounds exist:**
3. **Always-on-top** - KWin D-Bus API (KDE only) or restart app
4. **Global shortcuts** - KGlobalAccel (KDE) or pynput (other DEs)
5. **Clipboard persistence** - Persistent ClipboardManager instance

**Status:** See [Current Development Status](../../CLAUDE.md#current-development-status) in CLAUDE.md.

---

## Future Wayland Improvements

**Potential future enhancements:**

1. **XDG Desktop Portal integration:**
   - Standardized Wayland APIs for common tasks
   - Portal for global shortcuts (when widely supported)
   - May replace compositor-specific D-Bus APIs

2. **wlr-layer-shell protocol:**
   - Pin dialog to desktop layer (always visible)
   - Used by panels, docks, notifications
   - Requires compositor support (Sway has it, KWin implementing)

3. **Plasma Mobile integration:**
   - Kirigami mobile components for touch interfaces
   - Would benefit from Wayland-first design

**Reference:** [Wayland Protocols](https://gitlab.freedesktop.org/wayland/wayland-protocols)

---

## Related Documentation

- **[Troubleshooting: Wayland-Specific Issues](../getting-started/troubleshooting.md#wayland-specific-issues)**
- **[Design Decisions: KWin Window Management](design-decisions.md#kwin-window-management)**
- **[Patterns & Pitfalls: Wayland Considerations](../developer-guide/patterns-and-pitfalls.md)**
- **Code:** `blaze/kwin_rules.py`, `blaze/clipboard_manager.py`, `blaze/shortcuts.py`
