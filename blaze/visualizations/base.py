"""
Base classes and protocol for visualization patterns.
"""

from dataclasses import dataclass
from typing import Protocol
from collections import deque
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QPainterPath


@dataclass
class BandGeometry:
    """Geometry of the waveform donut band."""

    center: QPointF  # Center of the donut (mic center)
    r_inner: float  # Inner radius (edge of mic area)
    r_outer: float  # Outer radius (edge of waveform band)
    clip_path: QPainterPath  # Donut-shaped clip to prevent drawing under mic


@dataclass
class AudioState:
    """Current audio state for visualization rendering."""
    
    volume: float  # Current RMS volume, 0.0-1.0
    history: deque[float]  # Ring buffer of recent volume values
    peak: float  # Recent peak value
    time_s: float  # Monotonic time for animations
    
    def __post_init__(self):
        """Ensure history is a deque with reasonable max size."""
        if not isinstance(self.history, deque):
            self.history = deque(list(self.history), maxlen=64)


class VisualizationPattern(Protocol):
    """Protocol for all visualization patterns."""

    name: str  # e.g., "dots_radial"
    display_name: str  # e.g., "Radial Dot Rings"

    def paint(self, painter: QPainter, band: BandGeometry, audio: AudioState, params: dict) -> None:
        """Draw the visualization into the waveform band.

        Args:
            painter: QPainter to draw with
            band: BandGeometry defining the donut region
            audio: AudioState with current audio data
            params: Pattern-specific parameters from settings
        """
        ...
