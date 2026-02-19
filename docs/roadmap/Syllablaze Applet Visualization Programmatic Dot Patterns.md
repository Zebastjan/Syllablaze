# Syllablaze Applet Visualization â€” Programmatic Dot Patterns

**Status:** Design Proposal â€” February 17, 2026  
**Scope:** Replaces the previous visualization approach (Sections 5 and parts of Section 2 from the Recording Applet Design Plan) with a fully code-generated, pattern-selectable dot visualization system inside the waveform donut band.  
**Supersedes:** Earlier ideas about editing the SVG to embed visual elements behind the microphone, and the `inputlevel` overlay concept for the area under the mic.

---

## 1. Key Design Decisions

### 1.1 â€” Drop the "behind the mic" idea

The original plan included an `inputlevel` SVG elementâ€”a transparent overlay occupying the area *inside* the ring, directly behind the microphone iconâ€”intended to show color-mapped volume feedback (green â†’ yellow â†’ red tint).

**This is now dropped.** Painting anything behind the mic crowds the icon and muddies the clean silhouette that makes the applet glanceable. The microphone area stays untouched; all visualization energy goes into the **waveform donut band** surrounding the mic.

### 1.2 â€” All visualization is code-generated (no SVG editing per pattern)

The SVG asset (`syllablaze.svg`) remains a static structural resource. It provides:

| Element ID    | Role                                                         |
|---------------|--------------------------------------------------------------|
| `background`  | Blue gradient, always visible                                |
| `waveform`    | Transparent donut band â€” defines the drawing region          |
| `micgroup`    | Mic icon + border frame, always on top                       |
| `activearea`  | Transparent rect for click-zone / idle window sizing         |

No new SVG elements are added per visualization style. The `waveform` band is the canvas; the code paints dots, arcs, or other shapes into it using QPainter at render time. Adding a new style means adding a new Python class, not opening Inkscape.

### 1.3 â€” Dynamic window sizing: tight when idle, expanded when recording

This behavior was already outlined in the original plan (Section 4) but is restated here as a hard requirement because it directly affects the visualization experience:

**When idle (not recording):**
- The Qt widget shrinks to `boundsOnElement("activearea")` â€” the tightest bounding rectangle around the visible mic icon.
- This minimizes transparent dead space around the applet. On Wayland, transparent regions consume clicks rather than passing them through, so the smaller the idle window, the less interference with underlying applications.
- The waveform band is not visible; no dots are drawn.

**When recording:**
- The widget expands to `boundsOnElement("waveform")` â€” the full outer bounds of the donut band.
- The dot visualization is now active and visible within this expanded region.
- Small transparent corners at the edges of the bounding rect are tolerable during active recording.

**On state transition (idle â†’ recording or recording â†’ idle):**
- The window resizes centered on the same point so it doesn't jump.
- Transition can be instant initially; smooth animation is a future nicety.

```python
def set_recording_state(self, is_recording: bool):
    if is_recording:
        target = self.renderer.boundsOnElement("waveform")
    else:
        target = self.renderer.boundsOnElement("activearea")
    center = self.geometry().center()
    new_rect = self.svg_rect_to_widget(target)
    new_rect.moveCenter(center)
    self.setGeometry(new_rect)
    self.update()
```

---

## 2. Audio Data Pipeline (Shared by All Patterns)

All visualization patterns consume the same audio state object. No pattern needs to know how audio is captured â€” it just reads the current state each frame.

**Data sources available today:**
- `AudioManager.volume_changing(float)` â€” per-frame RMS volume, 0.0â€“1.0.
- A ring buffer of the last N volume values (e.g., N = 64), shifted each frame with the newest value appended.

**Data sources available later (FFT, when needed):**
- A window of raw audio samples (e.g., 1024 at 16 kHz = 64 ms).
- `numpy.fft.rfft` magnitude spectrum grouped into frequency bands.
- This is deferred until a pattern specifically needs frequency information.

**Shared audio state struct:**

```python
@dataclass
class AudioState:
    volume: float                   # Current RMS, 0.0â€“1.0
    history: deque[float]           # Ring buffer, most recent last
    peak: float                     # Recent peak (for color mapping)
    time_s: float                   # Monotonic time (for phase animation)
```

Each pattern's `paint()` method receives this struct plus the band geometry.

---

## 3. Pattern Architecture

### 3.1 â€” Common interface

Every visualization style implements a simple protocol:

```python
class VisualizationPattern(Protocol):
    name: str                       # e.g., "dots_radial"
    display_name: str               # e.g., "Radial Dot Rings"

    def paint(self, painter: QPainter, band: BandGeometry, audio: AudioState) -> None:
        """Draw the visualization into the waveform band."""
        ...
```

`BandGeometry` provides the donut's dimensions:

```python
@dataclass
class BandGeometry:
    center: QPointF                 # Center of the donut (mic center)
    r_inner: float                  # Inner radius (edge of mic area)
    r_outer: float                  # Outer radius (edge of waveform band)
    clip_path: QPainterPath         # Donut-shaped clip to prevent drawing under mic
```

### 3.2 â€” Pattern selection

The setting `applet_visualization` becomes an enum of pattern names:

| Setting value      | Class                  | Description                              |
|--------------------|------------------------|------------------------------------------|
| `dots_radial`      | `DotsRadialRings`      | Concentric dot rings, expanding wave     |
| `dots_curtains`    | `DotsSideCurtains`     | Left/right dot columns, volume-driven    |
| `dots_radar`       | `DotsRadarSweep`       | Rotating bright sector on a dot ring     |
| `bars_radial`      | `BarsRadialRing`       | Original radial bar design (from v1 plan)|
| `arcs_eq`          | `ArcsEqualizer`        | Arc segments as equalizer bands           |
| `sparkle`          | `SparkleField`         | Random flickering dots, volume-modulated |

The first three (`dots_radial`, `dots_curtains`, `dots_radar`) are the initial implementation targets. The rest are listed here for future reference. `bars_radial` preserves the original Level 1 bar design from the prior plan as a fallback option.

---

## 4. Initial Patterns â€” Detailed Specs

### 4.1 â€” DotsRadialRings (recommended first implementation)

**Visual concept:** Multiple concentric rings of evenly spaced dots fill the donut band. A "pressure wave" radiates outward from the inner edge, lighting up rings as it passes. Inspired by the Jitsi Meet expanding-dot animation.

**Dot layout:**
- Compute N_rings from the band width: `N_rings = floor((r_outer - r_inner) / dot_spacing)`, typically 4â€“6 rings.
- Each ring i has dots evenly spaced at angular intervals: `N_dots_per_ring = round(2Ï€ Ã— r_i / dot_spacing)` where `r_i = r_inner + i Ã— ring_gap`.
- Dots are circles of base radius ~2â€“3 px (at 100â€“200 px applet size).

**Animation behavior:**
- A wave phase Ï† advances over time: `Ï† += speed Ã— dt`, where `speed` is proportional to current volume (quiet = slow crawl, loud = fast pulse).
- Each dot's brightness = `max(0, 1 - |ring_index - Ï†| / falloff)`. The falloff controls the "thickness" of the wave â€” louder volume â†’ wider falloff â†’ more rings lit simultaneously.
- When the wave reaches the outermost ring, it wraps or bounces back inward.
- Dot radius can also pulse slightly with brightness for a subtle grow/shrink effect.

**Color:**
- Base hue from the applet's state color scheme (cool blue when recording normally, shifting toward warm tones if peaking).
- Brightness and alpha driven by the wave function above.
- Unlit dots: fully transparent (invisible), so the background gradient shows through.

**Parameters (hardcoded initially, tunable later):**

| Parameter       | Default | Description                                    |
|-----------------|---------|------------------------------------------------|
| `dot_spacing`   | 8 px    | Gap between dot centers                        |
| `dot_radius`    | 2.5 px  | Base dot radius                                |
| `wave_falloff`  | 1.5     | Rings lit on each side of the wave front       |
| `speed_min`     | 0.5     | Wave speed at volume = 0                       |
| `speed_max`     | 4.0     | Wave speed at volume = 1                       |
| `bounce`        | True    | Wave bounces vs. wraps at outer edge           |

---

### 4.2 â€” DotsSideCurtains

**Visual concept:** Two vertical (or gently arced) columns of dots, one to the left and one to the right of the mic, staying within the donut band. The dots brighten and inflate from the center outward as volume increases, like two "curtains" of energy expanding from the mic.

**Dot layout:**
- Left and right curtains are symmetric about the vertical center line.
- Each curtain is a column (or slight arc following the donut curvature) of dots from the top of the band to the bottom.
- Typically 8â€“12 dots per column, spaced evenly along the vertical extent of the band.
- Multiple columns per side (2â€“3) at different horizontal offsets within the band width, giving some depth.

**Animation behavior:**
- Each dot's brightness is a function of: (a) its distance from the horizontal center (closer = brighter at lower volumes), and (b) current volume.
- As volume increases, the "lit zone" expands outward â€” outer dots light up only at higher volumes.
- Dot radius scales with brightness: `radius = base_radius Ã— (0.5 + 0.5 Ã— brightness)`.
- A subtle vertical drift (dots shift slowly up or down over time) prevents the pattern from looking static even at constant volume.

**Color:**
- Same state-based color scheme as DotsRadialRings.

**Parameters:**

| Parameter        | Default | Description                                    |
|------------------|---------|------------------------------------------------|
| `dots_per_col`   | 10      | Dots in each vertical column                   |
| `columns_per_side` | 2     | Number of columns on each side                 |
| `dot_radius`     | 3 px    | Base dot radius                                |
| `expansion_curve`| 0.7     | How aggressively outer dots activate with volume|
| `drift_speed`    | 0.3     | Vertical drift rate (pixels per frame)         |

---

### 4.3 â€” DotsRadarSweep

**Visual concept:** A single ring of dots at the midpoint of the donut band. A bright "sweep" rotates around the ring like a radar, with a glowing head and a trailing fade. Rotation speed is driven by audio volume.

**Dot layout:**
- One ring of N dots (e.g., 32â€“48) evenly spaced at radius `r_mid = (r_inner + r_outer) / 2`.
- Optionally a second ring at a slightly different radius for visual density.

**Animation behavior:**
- A sweep angle Î¸ advances: `Î¸ += speed Ã— dt`, speed proportional to volume.
- Each dot's brightness = `max(0, 1 - angular_distance(dot_angle, Î¸) / trail_length)`.
- `trail_length` controls how many dots behind the head are still glowing (like a comet tail).
- At very low volume the sweep nearly stops, giving a calm "breathing" look; at high volume it spins fast.

**Color:**
- The sweep head can be a brighter or slightly different hue than the trail, giving a sense of directionality.

**Parameters:**

| Parameter       | Default | Description                                    |
|-----------------|---------|------------------------------------------------|
| `num_dots`      | 40      | Dots in the ring                               |
| `dot_radius`    | 2.5 px  | Base dot radius                                |
| `trail_length`  | Ï€/3     | Angular width of the fading trail (radians)    |
| `speed_min`     | 0.2     | Rotation speed at volume = 0 (rad/s)           |
| `speed_max`     | 6.0     | Rotation speed at volume = 1 (rad/s)           |
| `num_rings`     | 1       | 1 or 2 rings for visual density                |

---

## 5. Future Patterns (Deferred)

These are logged for reference but not part of the initial implementation:

### 5.1 â€” BarsRadialRing
The original Level 1 design from the prior plan: radial bars (lines, not dots) extending outward from `r_inner`, height driven by ring-buffer history. Preserved as a fallback style for users who prefer a classic equalizer look.

### 5.2 â€” ArcsEqualizer
Short arc segments within the donut, each representing a time slice (or later, a frequency band). Arcs thicken and brighten as energy increases. Requires the ring buffer for time-based mode; requires FFT for frequency-based mode.

### 5.3 â€” SparkleField
Pseudo-randomly placed dots within the full donut band that flicker in/out. Total active dot count and per-dot brightness modulated by volume. Gives an organic "energy cloud" feel.

### 5.4 â€” Organic Glow
The Level 3 concept from the prior plan: QRadialGradient with dynamic stops, or a small QImage with blur composited into the band. Most expensive; deferred until performance of simpler patterns is validated.

---

## 6. What Changed from the Prior Plan

| Topic | Prior Plan (Feb 17 v1) | This Document |
|-------|------------------------|---------------|
| `inputlevel` behind mic | Color-tinted overlay for volume feedback | **Dropped.** Nothing paints behind the mic. |
| Visualization drawing | Bars drawn by code, but single style (Level 1) | Multiple selectable dot/shape patterns, all code-generated |
| SVG edits per style | Each new visualization might need SVG changes | SVG is static; all styles draw into `waveform` band via QPainter |
| Pattern variety | Three levels (bars â†’ FFT â†’ glow), progressive | Six named patterns, three implemented initially, pluggable architecture |
| `applet_visualization` enum | `levelring`, `fftring`, `simpleglow` | `dots_radial`, `dots_curtains`, `dots_radar`, (+ future: `bars_radial`, `arcs_eq`, `sparkle`) |
| Window sizing (idle) | Shrink to `activearea` bounds | **Unchanged and re-emphasized:** tight to icon, minimal dead space |
| Window sizing (recording) | Expand to `waveform` bounds | **Unchanged and re-emphasized:** grows to full donut area |

---

## 7. Implementation Priority

| Priority | Task | Depends On |
|----------|------|------------|
| P1 | Define `VisualizationPattern` protocol + `BandGeometry` + `AudioState` | â€” |
| P1 | Implement `DotsRadialRings` | Protocol defined, `waveform` bounds available |
| P1 | Dynamic window sizing (idle â†’ recording) | `activearea` and `waveform` element IDs in SVG |
| P2 | Implement `DotsSideCurtains` | Protocol defined |
| P2 | Implement `DotsRadarSweep` | Protocol defined |
| P2 | Pattern selection setting in Settings UI | At least 2 patterns implemented |
| P3 | `BarsRadialRing` (port original bar design) | Protocol defined |
| P3 | `ArcsEqualizer` | Ring buffer or FFT data |
| P3 | `SparkleField` | Protocol defined |
| P3 | Per-pattern tunable parameters in settings | Pattern architecture stable |

---

## 8. Open Questions

1. **Dot count vs. performance at small sizes.** At 100 px applet size the donut band is narrow â€” do we cap dot count dynamically or use a fixed layout that looks good at both 100 px and 200 px?
2. **Smooth resize animation.** The current plan says "instant resize, animate later." Is the snap from icon-sized to donut-sized jarring enough to warrant an early animation pass?
3. **Color scheme customization.** Right now colors come from the state (recording = green, peaking = red). Should patterns have their own color override, or always follow the global state palette?

## What's Missing — The Actual Problem Claude Keeps Hitting

The docs describe **what to draw and where**, but they don't have a dedicated section on **how to correctly extract the donut geometry from the SVG and map it to widget coordinates**. That's the step where Claude keeps going wrong and inventing its own circle. Here's the supplemental write-up:

***

## CLAUDE.md Addendum: SVG Waveform Region — Geometry Extraction (MANDATORY)

> **This is the most common implementation error. Read before writing any visualization code.**

### The Hard Rule

**Never hardcode any radius, center point, or coordinate.** Every geometric value used in visualization drawing must be derived from the SVG element bounds at runtime. If you find yourself writing a number like `r_inner = 45` or `center_x = 100`, stop — that is wrong.

### Step 1: Load the renderer once

```python
self.renderer = QSvgRenderer("resources/syllablaze.svg")
```

### Step 2: Extract element bounds in SVG space

```python
# These are QRectF in SVG coordinate space
waveform_rect = self.renderer.boundsOnElement("waveform")   # the donut band
active_rect   = self.renderer.boundsOnElement("activearea") # idle click zone
```

### Step 3: Map SVG coordinates to widget coordinates

The SVG has its own internal coordinate system (e.g., 0–100 or 0–500). The widget has its own pixel size. These are **not the same**. You must map between them:

```python
def svg_rect_to_widget(self, svg_rect: QRectF) -> QRect:
    """Map a rect in SVG coordinate space to widget pixel space."""
    svg_size = self.renderer.defaultSize()       # QSize — SVG's native dimensions
    widget_size = self.size()                    # QSize — current widget pixel size
    
    x_scale = widget_size.width()  / svg_size.width()
    y_scale = widget_size.height() / svg_size.height()
    
    return QRect(
        int(svg_rect.x()      * x_scale),
        int(svg_rect.y()      * y_scale),
        int(svg_rect.width()  * x_scale),
        int(svg_rect.height() * y_scale)
    )
```

### Step 4: Derive donut geometry from the mapped rect

```python
def get_band_geometry(self) -> BandGeometry:
    waveform_widget_rect = self.svg_rect_to_widget(
        self.renderer.boundsOnElement("waveform")
    )
    
    # Center of the donut = center of the waveform bounding rect
    center = QPointF(waveform_widget_rect.center())
    
    # Outer radius = half the shorter dimension of the bounding rect
    r_outer = min(waveform_widget_rect.width(), 
                  waveform_widget_rect.height()) / 2.0
    
    # Inner radius: get the mic group bounds and use its outer edge
    mic_rect = self.svg_rect_to_widget(
        self.renderer.boundsOnElement("micgroup")
    )
    r_inner = min(mic_rect.width(), mic_rect.height()) / 2.0
    
    # Clip path: donut shape to prevent drawing under the mic
    clip = QPainterPath()
    clip.addEllipse(center, r_outer, r_outer)   # outer circle
    inner_path = QPainterPath()
    inner_path.addEllipse(center, r_inner, r_inner)
    clip = clip.subtracted(inner_path)           # punch out the mic area
    
    return BandGeometry(
        center=center,
        r_inner=r_inner,
        r_outer=r_outer,
        clip_path=clip
    )
```

### Step 5: Use the clip path in paintEvent

```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Render the full SVG first (background + mic)
    self.renderer.render(painter)
    
    # Get current band geometry
    band = self.get_band_geometry()
    
    # ALWAYS clip to the donut — this prevents drawing under the mic
    painter.setClipPath(band.clip_path)
    
    # Now hand off to the visualization pattern
    self.current_pattern.paint(painter, band, self.audio_state)
    
    painter.end()
```

### Why Claude Keeps Drawing a Circle Instead

The training data for "audio visualizer in a ring" almost universally uses
hardcoded geometry like `center = (width/2, height/2)` and
`radius = min(width, height) * 0.4`. Claude defaults to this pattern because
it's seen it thousands of times. The `boundsOnElement()` approach is rare in
training data. Putting this in `CLAUDE.md` as a **mandatory rule with the
word NEVER** is the only reliable way to override the default pattern. 
