"""
Pattern registry - imports and registers all available patterns.
"""

from .dots_radial import DotsRadialRings
from .dots_curtains import DotsSideCurtains
from .dots_radar import DotsRadarSweep

# Registry of all available patterns
PATTERNS = {
    "dots_radial": DotsRadialRings,
    "dots_curtains": DotsSideCurtains,
    "dots_radar": DotsRadarSweep,
}

# Ordered list for cycling
PATTERN_ORDER = ["dots_radial", "dots_curtains", "dots_radar"]


def get_pattern(pattern_name: str):
    """Get pattern class by name."""
    if pattern_name not in PATTERNS:
        raise ValueError(f"Unknown pattern: {pattern_name}")
    return PATTERNS[pattern_name]()


def get_next_pattern(current_pattern: str) -> str:
    """Get next pattern in cycle."""
    try:
        idx = PATTERN_ORDER.index(current_pattern)
        return PATTERN_ORDER[(idx + 1) % len(PATTERN_ORDER)]
    except ValueError:
        return PATTERN_ORDER[0]
