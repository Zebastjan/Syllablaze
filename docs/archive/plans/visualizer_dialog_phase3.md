# SVG-Based Visualizer Dialog - Phase 3 Complete

**Date:** 2025-02-14  
**Status:** ✅ Complete  
**Scope:** Create new SVG-based recording dialog with clean component architecture

## Summary

Successfully created a new SVG-based visualizer dialog with clean component separation. The new dialog features inner/outer region design with proper mouse handling and extensible visualizer architecture.

## New Components Created

### 1. VisualizerBase.qml
**Location:** `blaze/qml/components/visualizers/VisualizerBase.qml`  
**Purpose:** Abstract base class for all visualizers  
**Features:**
- Common interface: `isActive`, `samples`, `volume`
- Exponential smoothing for volume (factor: 0.7, configurable)
- Virtual `update()` method for subclasses
- Animation timer support (~60fps)

### 2. RadialWaveform.qml
**Location:** `blaze/qml/components/visualizers/RadialWaveform.qml`  
**Purpose:** Radial bar visualization (36 bars)  
**Features:**
- Canvas-based rendering (threaded, framebuffer)
- Color gradient: green → yellow → red based on amplitude
- 36 radial bars arranged in circle
- Smooth animation loop (~30fps)
- Bar dimensions: 4px width, 2-50px length

### 3. InnerRegion.qml
**Location:** `blaze/qml/components/InnerRegion.qml`  
**Purpose:** Interactive inner circle with SVG mic icon  
**Features:**
- SVG microphone icon with color overlay
- Dynamic colors: blue (idle) → green/yellow/red (recording)
- Circular mouse area for interaction
- Context menu (right-click)
- Drag-to-move support
- Scroll wheel resize
- Double-click to dismiss
- Single-click to toggle recording
- Transcribing indicator (purple bar)

### 4. OuterRegion.qml
**Location:** `blaze/qml/components/OuterRegion.qml`  
**Purpose:** Container for waveform visualizations  
**Features:**
- Visualizer loader with type switching
- Only visible during recording
- Transparent when inactive
- Supports multiple visualizer types (extensible)
- Currently supports: "radial", "none"

### 5. RecordingDialogVisualizer.qml
**Location:** `blaze/qml/RecordingDialogVisualizer.qml`  
**Purpose:** Main window assembling all components  
**Features:**
- Circular frameless window
- Combines InnerRegion + OuterRegion
- Size persistence (100-500px)
- Always-on-top support
- Proper z-ordering (outer behind inner)

## Architecture

```
RecordingDialogVisualizer (Window)
├── OuterRegion (visualization ring)
│   └── Loader
│       └── RadialWaveform (36 radial bars)
│           └── Canvas (threaded rendering)
└── InnerRegion (interactive center)
    ├── Background circle (recording state)
    ├── SVG mic icon + ColorOverlay
    ├── Transcribing indicator
    └── MouseArea (circular)
        ├── Click/double-click detection
        ├── Drag-to-move
        ├── Context menu
        └── Scroll resize
```

## Component Responsibilities

| Component | Responsibility | Inputs | Outputs |
|-----------|---------------|--------|---------|
| **InnerRegion** | User interaction | Mouse events | `toggleRecording()`, `dismissDialog()`, etc. |
| **OuterRegion** | Visualization host | `isActive`, `samples`, `volume` | Visual rendering |
| **RadialWaveform** | Draw waveform | `samples`, `volume` | Canvas rendering |
| **RecordingDialogVisualizer** | Window management | Bridge signals | Window show/hide |

## Mouse Interaction

**Inner Circle Only (70% of window):**
- ✅ Left click: Toggle recording
- ✅ Double click: Dismiss dialog
- ✅ Right click: Context menu (appears to side)
- ✅ Middle click: Open clipboard
- ✅ Drag: Move window
- ✅ Scroll: Resize window

**Outer Ring (30% of window):**
- ❌ No mouse events (visual only)

This prevents accidental interactions with the visualization area.

## Visual States

### Idle (Not Recording)
- Outer region: Hidden/transparent
- Inner icon: Blue color
- No waveform

### Recording (Normal Volume)
- Outer region: Visible with radial waveform
- Inner icon: Green color
- Waveform: Green bars

### Recording (High Volume)
- Outer region: Visible with radial waveform
- Inner icon: Yellow/Red color (based on volume)
- Waveform: Yellow/Red bars

### Transcribing
- Inner region: Purple indicator bar at bottom
- Opacity: Reduced to 0.5 (optional)

## Color Interpolation

**Idle → Recording:**
```
volume < 0.5:   Green → Yellow
volume >= 0.5:  Yellow → Red
```

Formula:
```javascript
// Green to Yellow (0.0-0.5)
t = volume * 2
color = green * (1-t) + yellow * t

// Yellow to Red (0.5-1.0)
t = (volume - 0.5) * 2
color = yellow * (1-t) + red * t
```

## Extensibility

### Adding New Visualizers

1. Create `NewVisualizer.qml` extending `VisualizerBase`
2. Implement `update(samples, volume)` method
3. Add to `OuterRegion.qml` loader:
   ```qml
   Component {
       id: newVisualizerComponent
       NewVisualizer {}
   }
   ```
4. Update switch case in `sourceComponent`

### Visualizer Types

Current:
- `radial` - 36 radial bars (default)
- `none` - No visualization

Future options:
- `spectrum` - FFT frequency bars
- `wave` - Oscilloscope waveform
- `particles` - Particle system
- `circle` - Breathing circle

## Settings Integration

The dialog uses the same `RecordingDialogBridge`:
- `isRecording` - Recording state
- `isTranscribing` - Transcription state
- `currentVolume` - Audio volume
- `audioSamples` - Waveform samples

Window management:
- `saveWindowSize(size)` - Save size on scroll
- `getWindowSize()` - Restore size on startup

## Testing

To test the new dialog:

1. **Manual test:**
   ```python
   # In Python console
   from blaze.recording_dialog_manager import RecordingDialogManager
   # Change QML path to RecordingDialogVisualizer.qml
   ```

2. **Verify components:**
   - [ ] Icon displays correctly
   - [ ] Color changes with recording state
   - [ ] Waveform appears during recording
   - [ ] Mouse interactions work in inner circle only
   - [ ] Scroll wheel resizes window
   - [ ] Size persists across restarts

3. **Compare with legacy:**
   - [ ] Same functionality
   - [ ] Better visual feedback
   - [ ] Cleaner code structure

## Migration Path

1. **Phase 3a** (Current): Components created, not integrated
2. **Phase 3b**: Add mode selector to settings
3. **Phase 3c**: Create RecordingDialogManagerV2 to load new dialog
4. **Phase 3d**: Test both dialogs side-by-side
5. **Phase 3e**: Make new dialog default
6. **Phase 3f**: Deprecate legacy dialog

## Files Created

1. `blaze/qml/components/visualizers/VisualizerBase.qml`
2. `blaze/qml/components/visualizers/RadialWaveform.qml`
3. `blaze/qml/components/InnerRegion.qml`
4. `blaze/qml/components/OuterRegion.qml`
5. `blaze/qml/RecordingDialogVisualizer.qml`

## Benefits

1. **Clean Architecture**: Single responsibility components
2. **Extensible**: Easy to add new visualizer types
3. **SVG-Based**: Scalable graphics, professional look
4. **Proper UX**: Inner circle interaction only
5. **Modern Design**: Radial waveform, color-coded feedback
6. **Maintainable**: ~400 lines vs ~530 in legacy

## Notes for Claude

- Components are independent and reusable
- Visualizer architecture supports future expansion
- Same bridge API as legacy dialog
- Ready for mode switching implementation
- No position-saving code (intentionally removed in Phase 1)
