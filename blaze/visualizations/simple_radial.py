"""
Simple radial waveform visualization - similar to the original working version.
"""

import math
import logging
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QColor, QPen
from .base import BandGeometry

logger = logging.getLogger(__name__)


class SimpleRadialBars:
    """Simple radial bars visualization - reliable and visible."""

    name = "simple_radial"
    display_name = "Radial Bars"

    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        """Draw simple radial bars using audio samples like QML."""
        num_bars = params.get("num_bars", 36)
        band_width = band.r_outer - band.r_inner
        min_length = 5  # Minimum visible bar length
        
        # Sensitivity for amplification (matching VolumeMeter)
        sensitivity = 0.002
        
        # Get audio samples from history (contains actual audio data, not just volume)
        # Convert deque to list for indexing
        samples = list(audio.history) if audio.history else []
        
        # Draw bars around the ring - each bar uses a different sample like QML
        for i in range(num_bars):
            angle = (i / num_bars) * 2 * math.pi - (math.pi / 2)
            
            # Get sample for this bar (like QML: audioSamples[sampleIndex])
            if samples:
                sample_idx = int((i / num_bars) * len(samples))
                raw_sample = abs(samples[sample_idx])
                # Amplify like VolumeMeter does (divide by sensitivity)
                sample_val = min(1.0, raw_sample / sensitivity)
            else:
                # Fallback to volume with same amplification
                sample_val = min(1.0, audio.volume / sensitivity)
            
            # Calculate bar length with minimum visible length (like QML)
            bar_length = min_length + (sample_val * (band_width - min_length) * 0.8)
            
            # Start at inner radius
            start_x = band.center.x() + math.cos(angle) * band.r_inner
            start_y = band.center.y() + math.sin(angle) * band.r_inner
            
            # End based on sample value
            end_radius = band.r_inner + bar_length
            end_x = band.center.x() + math.cos(angle) * end_radius
            end_y = band.center.y() + math.sin(angle) * end_radius
            
            # Color based on sample value (like QML color scheme)
            if sample_val < 0.5:
                color = QColor(0, 255, 100, 230)  # Green
            elif sample_val < 0.8:
                color = QColor(255, 255, 0, 230)  # Yellow
            else:
                color = QColor(255, 50, 50, 230)  # Red
            
            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
