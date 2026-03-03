"""
Base classes and protocol for visualization patterns.
"""

from dataclasses import dataclass
from typing import Protocol
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QPainterPath


@dataclass
class BandGeometry:
    """Geometry of the waveform donut band."""

    center: QPointF  # Center of the donut (mic center)
    r_inner: float  # Inner radius (edge of mic area)
    r_outer: float  # Outer radius (edge of waveform band)
    clip_path: QPainterPath  # Donut-shaped clip to prevent drawing under mic


class VisualizationPattern(Protocol):
    """Protocol for all visualization patterns."""

    name: str  # e.g., "dots_radial"
    display_name: str  # e.g., "Radial Dot Rings"

    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        """Draw the visualization into the waveform band.

        Args:
            painter: QPainter to draw with
            band: BandGeometry defining the donut region
            audio: AudioState from the waveform generator
            params: Pattern-specific parameters from config
        """
        ...
