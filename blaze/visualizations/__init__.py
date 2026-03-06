"""
Syllablaze visualization patterns for the recording applet.

This package contains various visualization patterns that can be selected
by the user to display audio activity in the waveform donut band.
"""

from .base import BandGeometry, VisualizationPattern, AudioState
from .simple_radial import SimpleRadialBars
from .dots_radial import DotsRadialRings
from .dots_curtains import DotsSideCurtains
from .dots_radar import DotsRadarSweep

# Pattern registry
PATTERNS: dict[str, type] = {
    'simple_radial': SimpleRadialBars,
    'dots_radial': DotsRadialRings,
    'dots_curtains': DotsSideCurtains,
    'dots_radar': DotsRadarSweep,
}

# Default pattern order for cycling
PATTERN_ORDER = ['simple_radial', 'dots_radial', 'dots_curtains', 'dots_radar']

def get_pattern(name: str) -> VisualizationPattern:
    """Get a pattern instance by name."""
    if name not in PATTERNS:
        raise ValueError(f"Unknown pattern: {name}. Available: {list(PATTERNS.keys())}")
    
    pattern_class = PATTERNS[name]
    return pattern_class()

def get_next_pattern(current: str) -> str:
    """Get the next pattern in the order for cycling."""
    if current not in PATTERN_ORDER:
        return PATTERN_ORDER[0]
    
    current_index = PATTERN_ORDER.index(current)
    next_index = (current_index + 1) % len(PATTERN_ORDER)
    return PATTERN_ORDER[next_index]

def get_all_patterns() -> dict:
    """Get all available patterns with their display names."""
    return {
        name: pattern_class.display_name 
        for name, pattern_class in PATTERNS.items()
    }
