"""
DotsRadialRings visualization pattern.
Concentric dot rings with expanding pressure wave.
"""

import numpy as np
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QColor
from .base import BandGeometry


class DotsRadialRings:
    """Multiple concentric rings of dots with radiating pressure wave."""

    name = "dots_radial"
    display_name = "Radial Dot Rings"

    def __init__(self):
        self.phase = 0.0  # Wave phase position
        self.direction = 1  # 1 = outward, -1 = inward

    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        """Draw radial dot rings with expanding wave."""
        # Get parameters with defaults
        dot_spacing = params.get("dot_spacing", 8)
        dot_radius = params.get("dot_radius", 2.5)
        wave_falloff = params.get("wave_falloff", 1.5)
        speed_min = params.get("speed_min", 0.5)
        speed_max = params.get("speed_max", 4.0)
        bounce = params.get("bounce", True)

        # Calculate number of rings
        band_width = band.r_outer - band.r_inner
        num_rings = max(3, int(band_width / dot_spacing))
        ring_gap = band_width / (num_rings - 1)

        # Update wave phase based on volume
        speed = speed_min + (speed_max - speed_min) * audio.volume
        self.phase += speed * 0.016  # Assuming ~60 FPS

        # Handle bounce or wrap
        if bounce:
            if self.phase >= num_rings - 1:
                self.direction = -1
                self.phase = num_rings - 1
            elif self.phase <= 0:
                self.direction = 1
                self.phase = 0
            self.phase += speed * 0.016 * self.direction
        else:
            self.phase = self.phase % num_rings

        # Set up clipping
        painter.setClipPath(band.clip_path)

        # Draw dots for each ring
        for ring_idx in range(num_rings):
            radius = band.r_inner + ring_idx * ring_gap

            # Calculate number of dots for this ring
            circumference = 2 * np.pi * radius
            num_dots = max(8, int(circumference / dot_spacing))

            # Calculate wave brightness for this ring
            ring_distance = abs(ring_idx - self.phase)
            brightness = max(0.0, 1.0 - ring_distance / wave_falloff)

            # Modulate brightness by current volume
            brightness *= 0.3 + 0.7 * audio.volume

            if brightness < 0.01:
                continue

            # Color: shift from blue to green based on volume, to red when peaking
            if audio.volume > 0.8:
                color = QColor(255, int(255 * (1 - brightness * 0.5)), 0)  # Orange-red
            elif audio.volume > 0.5:
                color = QColor(int(255 * brightness), 255, 0)  # Yellow-green
            else:
                color = QColor(
                    0, int(200 + 55 * brightness), int(255 * brightness)
                )  # Blue-cyan

            color.setAlphaF(brightness)
            painter.setBrush(color)
            painter.setPen(QColor(0, 0, 0, 0))

            # Draw dots around the ring
            for dot_idx in range(num_dots):
                angle = 2 * np.pi * dot_idx / num_dots
                x = band.center.x() + radius * np.cos(angle)
                y = band.center.y() + radius * np.sin(angle)

                # Pulse dot size with brightness
                current_radius = dot_radius * (0.7 + 0.3 * brightness)

                painter.drawEllipse(
                    QPointF(x - current_radius, y - current_radius),
                    current_radius * 2,
                    current_radius * 2,
                )
