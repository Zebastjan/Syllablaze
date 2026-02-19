***

# Syllablaze: Async, Synchronization & Window Management Best Practices

**Stack:** Python · PyQt6 · KDE Plasma 6 (Wayland) · KWin6 · KDE Frameworks 6 (Kirigami/KWindowSystem)

***

## The Core Rule

> **Never assume a Qt, KWin, or Wayland operation has completed just because the function call returned.**

KWin is a separate process. The Wayland compositor is a separate process. The clipboard is owned by the compositor. Returning from `setText()`, `show()`, or `setOnAllDesktops()` means "the request was sent" — not "the request was honored." Every timer used to wait for one of these operations to settle is a ticking time bomb. Use completion signals or proper event-loop patterns instead.  [doc.qt](https://doc.qt.io/qt-6/qclipboard.html)

***

## Anti-Patterns to Avoid

### ❌ The Timer Wait (most common offender)

```python
# WRONG — guessing how long the operation takes
self.clipboard.setText(text)
QTimer.singleShot(300, self.do_next_thing)   # "give it time to settle"
```

This is the anti-pattern that has already caused two separate bugs in Syllablaze. The delay is a guess. It passes in dev, breaks under load or on a slow Wayland compositor, and is invisible to code reviewers.  [forum.qt](https://forum.qt.io/topic/23550/making-asynchronous-calls-work-like-synchronous-calls)

`QTimer.singleShot(0, ...)` is *slightly* less bad — it defers to the next event loop tick rather than a wall-clock guess — but it still means "I don't know when this finished." Use it only as a last resort to break recursion, never to sequence dependent operations.  [forum.qt](https://forum.qt.io/topic/23550/making-asynchronous-calls-work-like-synchronous-calls)

### ❌ Setting Window Properties After `show()`

```python
# WRONG — KWin may process the map event before these flags arrive
window.show()
KWindowSystem.setOnAllDesktops(window.winId(), True)
window.setWindowFlag(Qt.WindowStaysOnTopHint)
```

KWin reads window properties at map time. Changes sent after `show()` trigger a second round-trip to the compositor, which may be ignored, applied late, or applied partially — producing the "flip the settings back and forth until it works" behavior you've been seeing.  [forum.qt](https://forum.qt.io/topic/143381/how-to-get-window-stays-on-top-in-plasma-wayland)

### ❌ Direct Window/Clipboard Calls from UI Widgets

```python
# WRONG — widget bypasses orchestrator, can't enforce ordering
class RecordingWidget(QWidget):
    def on_done(self):
        QApplication.clipboard().setText(result)  # direct call
        self.hide()
```

When widgets reach past the orchestrator to touch the clipboard or window state, the orchestrator loses the ability to sequence operations correctly.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_b38db527-4adb-4e72-b691-e1a0ee566586/3af71ab4-ee7d-4fde-aa55-e9ae5ba5ae78/5662e243.md)

***

## Correct Patterns

### ✅ Clipboard Writes: Wait for the Signal

On Wayland (Plasma 6), clipboard ownership is compositor-mediated. `QClipboard.setText()` is a request, not a write. The operation completes when `QClipboard.dataChanged` fires.  [doc.qt](https://doc.qt.io/qt-6/qclipboard.html)

```python
class ClipboardManager(QObject):
    clipboard_ready = pyqtSignal(str)

    def write(self, text: str):
        self._pending_text = text
        clip = QApplication.clipboard()
        clip.dataChanged.connect(self._on_clipboard_confirmed)
        clip.setText(text)

    def _on_clipboard_confirmed(self):
        clip = QApplication.clipboard()
        clip.dataChanged.disconnect(self._on_clipboard_confirmed)
        if clip.text() == self._pending_text:
            self.clipboard_ready.emit(self._pending_text)
```

**Wayland-specific caveat:** On Wayland, clipboard contents are lost when the owning process closes its window or loses focus, because the compositor holds a reference to the source process.  [blog.martin-graesslin](https://blog.martin-graesslin.com/blog/2016/07/synchronizing-the-x11-and-wayland-clipboard/) If Syllablaze hides its window before the target app reads the clipboard, the paste will fail silently. The fix is to keep the window alive (even if invisible) until after the paste event, or use a clipboard persistence mechanism like `xclip -loops 1` / `wl-copy --paste-once`.

KDE Frameworks 6.22 (January 2026) specifically patched multiple clipboard-related issues on Wayland, including data loss on window close. Ensure the KF6 dependency is pinned to ≥ 6.22.  [linuxtoday](https://www.linuxtoday.com/blog/kde-frameworks-6-22-fixes-multiple-clipboard-related-issues-on-wayland/)

### ✅ Window Setup: Configure Before Showing

All window flags, attributes, and KWin properties must be set **before** `show()` is called. This is not a style preference — it is a Wayland protocol constraint.  [forum.qt](https://forum.qt.io/topic/143381/how-to-get-window-stays-on-top-in-plasma-wayland)

```python
def _prepare_window(self, window: QWidget):
    # Step 1: set all Qt flags
    window.setWindowFlags(
        Qt.Tool |
        Qt.FramelessWindowHint |
        Qt.WindowStaysOnTopHint
    )
    window.setAttribute(Qt.WA_TranslucentBackground)
    window.setAttribute(Qt.WA_ShowWithoutActivating)

    # Step 2: connect to the exposed signal to apply KWin-level properties
    # windowHandle() is not valid until after show(), but the signal fires after map
    window.show()  # NOW show — Qt flags are already set
    # Step 3: apply KWindowSystem properties once the handle exists
    QTimer.singleShot(0, lambda: self._apply_kwin_props(window))

def _apply_kwin_props(self, window: QWidget):
    wid = window.winId()
    if wid:
        KWindowSystem.setOnAllDesktops(wid, True)
        KWindowSystem.setState(wid, NET.KeepAbove)
```

The `singleShot(0)` here is legitimate: `winId()` is not valid until the window has been mapped, and deferring one tick guarantees the handle exists. This is the approved use.  [forum.qt](https://forum.qt.io/topic/23550/making-asynchronous-calls-work-like-synchronous-calls)

### ✅ KWindowSystem vs. Raw Qt Flags on Wayland

On Wayland, raw Qt window flags (`Qt.WindowStaysOnTopHint`, `X11BypassWindowManagerHint`) are **unreliable or non-functional**. They are implemented as hints in the X11 protocol; Wayland compositors are not required to honor them.  [forum.qt](https://forum.qt.io/topic/143381/how-to-get-window-stays-on-top-in-plasma-wayland)

Use `KWindowSystem` (from `PyKF6.KWindowSystem` or via D-Bus) for any KDE/Plasma-specific window behavior:

| Intent | X11 | Wayland |
|---|---|---|
| Always on top | `Qt.WindowStaysOnTopHint` | `KWindowSystem.setState(wid, NET.KeepAbove)` |
| All desktops | `NET.WMDesktop = 0xFFFFFFFF` | `KWindowSystem.setOnAllDesktops(wid, True)` |
| Skip taskbar | `Qt.Tool` flag | `KWindowSystem.setState(wid, NET.SkipTaskbar)` |
| Skip pager | `Qt.Tool` flag | `KWindowSystem.setState(wid, NET.SkipPager)` |

`KWindowSystem` provides a unified API that works on both X11 and Wayland by routing through the correct protocol automatically.  [forum.qt](https://forum.qt.io/topic/143381/how-to-get-window-stays-on-top-in-plasma-wayland)

### ✅ Signal/Slot Ordering: Never Rely on Fan-Out Order

When multiple slots are connected to the same signal, Qt executes them in connection order — but this is fragile across refactors.  [forum.qt](https://forum.qt.io/topic/86756/signal-slot-process-order-in-function)

If operation B must always happen after operation A completes, use a **chain**, not fan-out:

```python
# FRAGILE: relies on connection order
self.transcription_ready.connect(self.clipboard_manager.write)
self.transcription_ready.connect(self.window_manager.hide_progress)

# CORRECT: explicit chain with completion signal
self.transcription_ready.connect(self.clipboard_manager.write)
self.clipboard_manager.clipboard_ready.connect(self.window_manager.hide_progress)
```

The second form makes the dependency explicit in the code and in the signal graph.  [youtube](https://www.youtube.com/watch?v=wOgP64wSE6U)

Cross-thread signal emissions (e.g., audio thread → main thread) are automatically queued by Qt, but the ordering guarantee only holds *within* a single thread's event queue. If two threads can both emit signals to the same slot, protect the emission with a mutex.  [youtube](https://www.youtube.com/watch?v=wOgP64wSE6U)

### ✅ The Atomic Setup Pattern for Applet Initialization

The "flip settings back and forth to make it work" symptom means state is being applied incrementally and reaching a valid configuration only accidentally. The fix is to have a single `_apply_state()` method that transitions the window atomically from its current state to the target state:

```python
def _apply_applet_state(self, state: AppletState):
    """Single point of truth. Called once per state transition."""
    # Compute target configuration
    target_flags = self._flags_for_state(state)
    target_size = self._size_for_state(state)
    target_kwin = self._kwin_props_for_state(state)

    # Apply atomically: hide → reconfigure → show
    was_visible = self.isVisible()
    if was_visible:
        self.hide()

    self.setWindowFlags(target_flags)
    self.resize(target_size)

    if was_visible or state.should_be_visible:
        self.show()
        QTimer.singleShot(0, lambda: self._apply_kwin_props(target_kwin))
```

Never mutate window state piecemeal from multiple callsites.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_b38db527-4adb-4e72-b691-e1a0ee566586/b45ca243-cd24-4680-b0c4-4b1309752c12/2ba60cc4.md)

***

## Orchestrator Responsibility Rules

These rules map directly onto the `SyllablazeOrchestrator` / `WindowManager` / `ClipboardManager` architecture:

1. **Only `WindowManager` calls `show()`, `hide()`, or `setWindowFlags()`** on any window. No widget touches another widget's visibility.
2. **Only `ClipboardManager` calls `clipboard.setText()`**. It owns the write and emits `clipboard_ready` when confirmed.
3. **`WindowManager` waits for `clipboard_ready` before hiding the progress window** — not for a timer, not for `transcription_ready`.
4. **All KWin/KWindowSystem calls go through `WindowManager`**. It is the only class that knows about `winId()` timing and KWin round-trips.
5. **No `QTimer` with a non-zero interval in any manager class.** If you find yourself writing `QTimer.singleShot(500, ...)`, stop and find the completion signal.

***

## Quick Reference: "What Do I Wait For?"

| Operation | Don't use timer — wait for... |
|---|---|
| `clipboard.setText(text)` | `clipboard.dataChanged` + verify `clipboard.text() == text` |
| `window.show()` + KWin props | `QTimer.singleShot(0, ...)` after `show()` (winId timing only) |
| `window.hide()` before clipboard paste | `clipboard_manager.clipboard_ready` signal |
| KWin `setOnAllDesktops` | No completion signal exists — set before `show()` to avoid the race entirely |
| Audio thread transcription done | `RecordingController.transcription_complete` signal |
| Settings change applied | `SettingsService.setting_changed` signal |

---
