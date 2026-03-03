# Syllablaze Visualization Test App

A standalone test application for experimenting with audio visualization patterns before integrating them into the main Syllablaze application.

## Purpose

This app allows you to:
- Test visualization patterns with simulated voice-like audio data
- Tune parameters in real-time via TOML configuration
- Iterate quickly on visual designs without restarting the main app

## Running the App

```bash
cd tests/visualization_test
python main.py
```

Or from the project root:

```bash
python tests/visualization_test/main.py
```

## Controls

| Action | Button | Description |
|--------|--------|-------------|
| **Play/Pause** | Left-click | Toggle the audio simulation |
| **Switch Pattern** | Middle-click | Cycle through visualization patterns |
| **Edit Config** | Right-click | Open `viz_config.toml` in helix editor |
| **Move Window** | Drag | Click and drag to reposition the window |

## Configuration

Edit `viz_config.toml` to adjust visualization parameters:

```toml
# Current visualization pattern
# Options: dots_radial, dots_curtains, dots_radar
current_pattern = "dots_radial"

[dots_radial]
dot_spacing = 8
dot_radius = 2.5
wave_falloff = 1.5
speed_min = 0.5
speed_max = 4.0
bounce = true
```

Changes are applied **immediately** when you save the file!

## Visualization Patterns

### 1. DotsRadialRings (Recommended First)
Multiple concentric rings of dots with a radiating pressure wave. The wave expands outward from the center, with speed and intensity driven by the simulated audio volume.

**Inspired by:** Jitsi Meet expanding-dot animation

### 2. DotsSideCurtains
Two vertical columns of dots on the left and right sides of the microphone icon. Dots brighten and expand outward as volume increases, like curtains of energy.

### 3. DotsRadarSweep
A single ring of dots with a rotating "radar" sweep. The sweep rotates faster as volume increases, with a glowing head and trailing fade effect.

## Audio Simulation

The app generates realistic voice-like audio data:
- **Syllable-based envelopes** - Natural attack, sustain, and release phases
- **Breathing simulation** - Subtle rhythmic variation
- **Random bursts** - Simulates speech onset
- **Smooth transitions** - No jarring jumps in volume

## Architecture

```
tests/visualization_test/
├── main.py                 # Entry point
├── main_window.py          # Frameless window with SVG + visualization
├── audio_generator.py      # Voice-like waveform simulation
├── config.py              # TOML config with auto-reload
├── viz_config.toml        # Configuration file
├── patterns/
│   ├── __init__.py        # Pattern registry
│   ├── base.py            # Protocol and dataclasses
│   ├── dots_radial.py     # DotsRadialRings pattern
│   ├── dots_curtains.py   # DotsSideCurtains pattern
│   └── dots_radar.py      # DotsRadarSweep pattern
└── README.md              # This file
```

## Adding New Patterns

1. Create a new file in `patterns/`:

```python
from .base import BandGeometry

class MyNewPattern:
    name = "my_pattern"
    display_name = "My New Pattern"
    
    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        # Your drawing code here
        pass
```

2. Register in `patterns/__init__.py`:

```python
from .my_pattern import MyNewPattern

PATTERNS = {
    # ... existing patterns ...
    'my_pattern': MyNewPattern,
}

PATTERN_ORDER = ['dots_radial', 'dots_curtains', 'dots_radar', 'my_pattern']
```

3. Add default parameters to `viz_config.toml`:

```toml
[my_pattern]
param1 = 10
param2 = 2.5
```

## Integration with Main App

Once you're happy with a visualization:

1. Copy the pattern file from `patterns/` to the main app's visualization directory
2. Wire up the audio data from the real `AudioManager`
3. Add the pattern to the main app's settings UI

The pattern code is designed to be portable - just swap out the simulated `AudioState` for the real one!
