# Syllablaze Recording Applet â€” Design & Implementation Plan

> **Status:** Proposal â€” February 2026  
> **Scope:** The SVG-based recording applet widget, its visualization, interaction modes, SVG structure, new settings, and tray icon fixes.

---

## 1. Overview

The Recording Applet is a floating widget that provides visual feedback during recording and transcription. It replaces (or supplements) the legacy square recording dialog with a richer, icon-based experience built on the `syllablaze.svg` asset rendered via Qt's `QSvgRenderer`.

### Design Goals
- Provide clear, glanceable recording status from any desktop
- Show real-time audio visualization (not just a green block)
- Support multiple interaction preferences (keyboard, mouse, both)
- Minimize interference with underlying applications (no dead click zones)
- Maintain clean separation from the backend (all interaction through the orchestrator)

---

## 2. SVG Asset Structure

The SVG (`resources/syllablaze.svg`) must contain these named elements in the following z-order (bottom to top):

| Layer (bottom â†’ top) | Element ID | Fill | Purpose |
|---|---|---|---|
| 1. Background gradient | `background` | Blue gradient (always visible) | Base visual state; the "quiet" look of the applet |
| 2. Input level overlay | `input_level` | Transparent (alpha = 0) | Area inside the ring + under the mic. Software paints input level feedback here (e.g., color intensity mapped to volume) |
| 3. Waveform donut | `waveform` | Transparent (alpha = 0) | The ring-shaped band around the mic. Software paints the audio visualization here |
| 4. Microphone + border | `mic_group` | Original mic artwork | The mic icon and its border frame; always rendered on top so visualization never covers it |
| 5. Active click area | `active_area` | Transparent (alpha = 0) | A rectangle (or rounded rect) covering the full visible applet area. Used by Qt to determine clickable region and window sizing |

### SVG Editing Checklist (Inkscape)
- [ ] Duplicate the blue gradient rounded rect â†’ keep original as `background`, duplicate as `input_level` (set alpha to 0)
- [ ] Ensure the existing donut path has id `waveform`
- [ ] Group mic + border elements â†’ set group id to `mic_group`
- [ ] Add a new transparent rect covering the full visible icon â†’ set id to `active_area`
- [ ] Verify z-order in Inkscape's Objects panel: `background` at bottom, `active_area` at top
- [ ] Push `syllablaze.svg` to `resources/` in the repo

---

## 3. Interaction Modes

Three user-selectable modes, configured via Settings:

### Mode 1: Off
- The SVG applet is **not shown**.
- User relies on keyboard shortcuts (Ctrl+Alt+R) and tray icon.
- Optionally, the **legacy square dialog** can be enabled as a popup for recording feedback.
- The legacy dialog should be made smaller than its current size.

### Mode 2: Persistent
- The applet is **always visible** as a floating widget.
- User can **click to start/stop recording** and **drag to reposition**.
- Widget stays on screen across desktop switches.
- When idle: shows the mic icon at rest (background gradient visible).
- When recording: expands to show waveform ring + input level feedback.

### Mode 3: Popup
- The applet **appears when recording starts** and **disappears when transcription completes**.
- Pops up on the **current desktop** where the user initiated recording.
- Provides the same visual feedback as Persistent mode, but only during active use.

### New Settings Required
| Setting | Type | Default | Description |
|---|---|---|---|
| `applet_mode` | Enum: `off`, `persistent`, `popup` | `popup` | Which applet interaction mode to use |
| `legacy_dialog_enabled` | Bool | `false` | Show the square recording dialog (useful when applet is off) |
| `applet_visualization` | Enum: `level_ring`, `fft_ring`, `simple_glow` | `level_ring` | Which visualization style to use |

---

## 4. Window Sizing & Click Handling

### The Problem
Transparent areas of the applet window create "dead zones" where clicks don't reach underlying applications. On Wayland, `Qt::WindowTransparentForInput` does **not** work reliably â€” clicks on transparent regions are consumed by the window rather than passed through.

### The Solution: Dynamic Window Resizing

**When idle / not recording:**
- Size the Qt widget to `boundsOnElement("active_area")` â€” the tightest rectangle around the visible mic icon.
- This minimizes transparent corner dead zones to a few pixels (acceptable).

**When recording / visualizing:**
- Expand the widget to `boundsOnElement("waveform")` outer bounds â€” the full donut area.
- The waveform ring is visually active, so users expect to interact with this region.
- Small transparent corners at the edges of the bounding rect are tolerable during active recording.

**On state transition (idle â†” recording):**
- Animate or instant-resize the window.
- Keep the window **centered** on the same point so it doesn't jump around.

### Implementation
```python
# In the applet widget's state change handler:
def set_recording_state(self, is_recording: bool):
    if is_recording:
        target = self.renderer.boundsOnElement("waveform")
    else:
        target = self.renderer.boundsOnElement("active_area")
    
    # Map SVG coords to widget coords, resize, re-center
    center = self.geometry().center()
    new_rect = self._svg_rect_to_widget(target)
    new_rect.moveCenter(center)
    self.setGeometry(new_rect)
    self.update()
```

---

## 5. Audio Visualization

### Current State
The waveform area currently shows a **solid green fill** when recording is active. This is because:
- `AudioManager` emits a single `volume_changing(float)` signal (0.0â€“1.0).
- The applet paints the `waveform` region with a flat color at that alpha.
- There is no time-series buffer or frequency analysis feeding the visualization.

### Visualization Approaches

#### Level 1: Radial Level Ring (Recommended First Step)
A ring of bars around the mic that pulse with recent volume history.

**Data pipeline:**
1. `AudioManager` already provides per-frame RMS volume via `volume_changing`.
2. Maintain a **ring buffer** of the last N values (e.g., N = 64 for 64 bars around the ring).
3. Each frame, shift values and append the newest.

**Drawing approach:**
- The donut region defines an inner radius `r_inner` and outer radius `r_outer` (computed from `waveform` bounds).
- For each bar `i` (0..N-1), compute angle `Î¸ = 2Ï€ Ã— i / N`.
- Bar height = `r_inner + value[i] Ã— (r_outer - r_inner)`.
- Draw a line or thin wedge from `(r_inner, Î¸)` to `(bar_height, Î¸)` in polar coordinates, converted to Cartesian.

**Sketch:**
```python
import math
from collections import deque

class RadialLevelRing:
    def __init__(self, num_bars=64):
        self.num_bars = num_bars
        self.values = deque([0.0] * num_bars, maxlen=num_bars)
    
    def push_value(self, volume: float):
        self.values.append(min(1.0, volume))
    
    def paint(self, painter, center, r_inner, r_outer, color):
        band = r_outer - r_inner
        for i, val in enumerate(self.values):
            angle = 2 * math.pi * i / self.num_bars
            r = r_inner + val * band
            x0 = center.x() + r_inner * math.cos(angle)
            y0 = center.y() - r_inner * math.sin(angle)
            x1 = center.x() + r * math.cos(angle)
            y1 = center.y() - r * math.sin(angle)
            painter.setPen(QPen(color, 2))
            painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
```

This is lightweight (no FFT), looks animated and alive, and naturally fills the donut shape.

#### Level 2: FFT Frequency Ring (Future Enhancement)
Map frequency bins to positions around the ring for a spectrum-analyzer look.

**Data pipeline:**
1. Instead of just RMS, capture a **window of raw audio samples** (e.g., 1024 samples at 16kHz = 64ms).
2. Apply `numpy.fft.rfft()` to get magnitude spectrum.
3. Group into N frequency bands (e.g., 32 bands, log-scaled).

**Drawing approach:**
- Same radial bar technique as Level 1, but each bar represents a frequency band's magnitude instead of a time-series volume value.
- Low frequencies at the top, high frequencies wrapping around (or vice versa).

**Performance note:** NumPy FFT on 1024 samples is extremely fast (~0.1ms); the bottleneck is QPainter drawing, which can be optimized by batching `drawLines()` calls.

#### Level 3: Organic Glow / Blob (Future Enhancement)
A smooth, amorphous glow that fills the donut with color intensity mapped to volume/frequency.

- Use `QRadialGradient` with dynamic stop positions based on audio energy.
- Or render to a small `QImage` buffer and apply a blur, then composite into the donut using a clip path.
- Most visually appealing but most expensive; defer until Level 1/2 are working.

### Integration with `input_level`
The `input_level` element (area inside ring + under mic) provides a simpler feedback channel:
- Map current volume to the **opacity or color intensity** of this region.
- E.g., quiet = fully transparent (shows `background` gradient); loud = semi-opaque green/red tint.
- This gives instant "am I peaking?" feedback even at a glance.

Color mapping suggestion:
| Volume | Color |
|---|---|
| 0.0 â€“ 0.5 | Transparent â†’ light green tint |
| 0.5 â€“ 0.8 | Green â†’ yellow tint |
| 0.8 â€“ 1.0 | Yellow â†’ red tint (peaking!) |

---

## 6. Tray Icon Issues

### Problem
The system tray keeps showing the old `syllablaze.png` even though it was deleted from the repo. The new SVG should be used instead.

### Root Causes
1. **KDE icon cache:** Plasma caches icon data aggressively. Deleting the source file doesn't clear the cache.
2. **Stale `.desktop` file:** `resources/org.kde.syllablaze.desktop` or a copy in `~/.local/share/applications/` may still reference the old PNG path.
3. **Code fallback:** In `blaze/main.py`, `ApplicationTrayIcon.initialize()` has a fallback chain that tries `syllablaze.png` from the local directory.

### Fixes
1. **Clear KDE icon caches:**
   ```bash
   rm -f ~/.cache/icon-cache.kcache
   rm -f ~/.cache/ksycoca5_*
   rm -f ~/.cache/plasma-svgelements-*
   rm -f ~/.cache/plasma_theme_*
   ```
   Then log out and back in.

2. **Update `.desktop` file:**
   - Change `Icon=syllablaze` (no extension) so KDE looks up the icon by name from the theme/standard paths.
   - Install `syllablaze.svg` to `~/.local/share/icons/hicolor/scalable/apps/syllablaze.svg`.

3. **Update icon loading in `main.py`:**
   ```python
   # In ApplicationTrayIcon.initialize():
   self.app_icon = QIcon.fromTheme("syllablaze")
   if self.app_icon.isNull():
       # Fallback to local SVG, not PNG
       local_icon_path = os.path.join(
           os.path.dirname(os.path.abspath(__file__)), 
           "..", "resources", "syllablaze.svg"
       )
       if os.path.exists(local_icon_path):
           self.app_icon = QIcon(local_icon_path)
   ```

4. **Recording state tray icon:**
   - When recording starts, swap the tray icon to a version with a **bright red pulsing dot** overlay.
   - Use a `QTimer` to toggle between normal and red-dot variants at ~1Hz for a slow flash effect.
   - This provides feedback even when the applet is on a different desktop.

---

## 7. Multi-Desktop Behavior

### Problem
When using multiple virtual desktops in KDE Plasma, the applet may not be visible on the current desktop, and keyboard-shortcut-initiated recording gives no visual feedback.

### Solutions

**For Popup mode:**
- The popup inherently appears on the current desktop (Qt creates new windows on the active desktop by default).
- No special handling needed.

**For Persistent mode:**
- Set the window flags to include `Qt::WindowStaysOnTopHint` and potentially use KDE-specific window rules to "show on all desktops."
- In KWin/Wayland, this can be done via:
  ```python
  # After creating the applet widget:
  from subprocess import run
  run(["kdotool", "windowrule", "--class", "syllablaze", "alldesktops"])
  ```
  Or set the `_NET_WM_DESKTOP` property to `0xFFFFFFFF` (all desktops) on X11.
- The more portable approach: add a "Show on all desktops" checkbox in settings and use `self.setWindowFlag(Qt.WindowType.X11BypassWindowManagerHint)` cautiously, or let the user pin it via KWin's own window menu.

**Tray icon as universal fallback:**
- The tray icon is always visible regardless of desktop.
- A flashing red recording indicator on the tray ensures the user always knows recording is active.

---

## 8. Implementation Priority

| Priority | Task | Depends On |
|---|---|---|
| **P0** | Edit SVG: add `background`, `input_level`, `active_area` IDs; push to repo | Inkscape session |
| **P0** | Fix tray icon: clear cache, update code to use SVG, add red flash for recording | SVG in repo |
| **P1** | Implement three applet modes (off / persistent / popup) with settings | Orchestrator API |
| **P1** | Dynamic window sizing (idle vs recording) | SVG element IDs |
| **P1** | Radial level ring visualization (Level 1) | `AudioManager` volume signal + ring buffer |
| **P2** | Input level color feedback (green â†’ yellow â†’ red) | `input_level` SVG element |
| **P2** | Legacy dialog size reduction | â€” |
| **P2** | Multi-desktop "show on all desktops" for persistent mode | KWin/Wayland research |
| **P3** | FFT frequency ring visualization (Level 2) | NumPy FFT integration |
| **P3** | Organic glow visualization (Level 3) | QRadialGradient + clip |
| **P3** | New settings UI for applet mode / visualization style | Settings window |
