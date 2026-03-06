"""
DotsRadarSweep visualization pattern.
Rotating radar sweep on a ring of dots.
"""

import numpy as np
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QColor
from .base import BandGeometry


class DotsRadarSweep:
    """A rotating radar sweep on a single ring of dots."""

    name = "dots_radar"
    display_name = "Radar Sweep"

    def __init__(self):
        self.sweep_angle = 0.0  # Current sweep angle in radians

    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        """Draw radar sweep on dot ring."""
        # Get parameters with defaults
        num_dots = params.get("num_dots", 40)
        dot_radius = params.get("dot_radius", 2.5)
        trail_length = params.get("trail_length", np.pi / 3)
        speed_min = params.get("speed_min", 0.2)
        speed_max = params.get("speed_max", 6.0)
        num_rings = params.get("num_rings", 1)

        # Amplify volume for better visualization (input is often very quiet)
        # Using VolumeMeter-style sensitivity: volume / 0.002 for full scale
        sensitivity = 0.002
        display_volume = min(1.0, audio.volume / sensitivity)
        # Ensure minimum visibility so there's always some activity
        display_volume = max(0.15, display_volume)

        # Calculate sweep speed based on volume
        speed = speed_min + (speed_max - speed_min) * display_volume
        self.sweep_angle += speed * 0.016  # Update angle
        self.sweep_angle = self.sweep_angle % (2 * np.pi)

        # Set up clipping
        painter.setClipPath(band.clip_path)

        # Draw dots on ring(s)
        for ring_idx in range(num_rings):
            # Calculate ring radius
            if num_rings == 1:
                radius = (band.r_inner + band.r_outer) / 2
            else:
                t = ring_idx / (num_rings - 1)
                radius = band.r_inner + t * (band.r_outer - band.r_inner)

            # Draw each dot
            for dot_idx in range(num_dots):
                dot_angle = 2 * np.pi * dot_idx / num_dots

                # Calculate angular distance from sweep (handle wrap-around)
                angle_diff = abs(dot_angle - self.sweep_angle)
                angle_diff = min(angle_diff, 2 * np.pi - angle_diff)

                # Calculate brightness based on distance from sweep head
                if angle_diff > trail_length:
                    brightness = 0.0
                else:
                    # Head is brightest, trail fades
                    brightness = 1.0 - (angle_diff / trail_length) ** 2

                # Modulate overall brightness by volume
                brightness *= 0.2 + 0.8 * display_volume

                if brightness < 0.01:
                    continue

                # Color: head is different from trail
                if angle_diff < 0.1:
                    # Sweep head - bright white/yellow
                    color = QColor(255, 255, int(200 * brightness))
                else:
                    # Trail - gradient from yellow to blue
                    trail_factor = angle_diff / trail_length
                    if display_volume > 0.7:
                        r = 255
                        g = int(255 * (1 - trail_factor * 0.5))
                        b = 0
                    elif display_volume > 0.4:
                        r = int(255 * (1 - trail_factor))
                        g = 255
                        b = int(100 * trail_factor)
                    else:
                        r = 0
                        g = int(200 + 55 * (1 - trail_factor))
                        b = int(255 * (1 - trail_factor * 0.5))
                    color = QColor(r, g, b)

                color.setAlphaF(brightness)
                painter.setBrush(color)
                painter.setPen(QColor(0, 0, 0, 0))

                # Calculate dot position
                x = band.center.x() + radius * np.cos(dot_angle)
                y = band.center.y() + radius * np.sin(dot_angle)

                # Pulse size with brightness
                current_radius = dot_radius * (0.8 + 0.4 * brightness)

                painter.drawEllipse(
                    QPointF(x - current_radius, y - current_radius),
                    current_radius * 2,
                    current_radius * 2,
                )

        # Draw a subtle glow at the sweep head
        head_x = band.center.x() + ((band.r_inner + band.r_outer) / 2) * np.cos(
            self.sweep_angle
        )
        head_y = band.center.y() + ((band.r_inner + band.r_outer) / 2) * np.sin(
            self.sweep_angle
        )

        glow_radius = dot_radius * 3 * display_volume
        if glow_radius > 1:
            from PyQt6.QtGui import QRadialGradient

            gradient = QRadialGradient(head_x, head_y, glow_radius)
            if display_volume > 0.7:
                gradient.setColorAt(0, QColor(255, 200, 0, 150))
            else:
                gradient.setColorAt(0, QColor(0, 255, 200, 100))
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(gradient)
            painter.drawEllipse(
                QPointF(head_x - glow_radius, head_y - glow_radius),
                glow_radius * 2,
                glow_radius * 2,
            )
