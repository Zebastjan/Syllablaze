"""
DotsSideCurtains visualization pattern.
Left/right dot columns expanding with volume.
"""

import numpy as np
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QColor
from .base import BandGeometry


class DotsSideCurtains:
    """Two vertical columns of dots expanding from the center with volume."""

    name = "dots_curtains"
    display_name = "Side Curtains"

    def __init__(self):
        self.drift_offset = 0.0  # For vertical drift animation

    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        """Draw side curtain dot columns."""
        # Get parameters with defaults
        dots_per_col = params.get("dots_per_col", 10)
        columns_per_side = params.get("columns_per_side", 2)
        dot_radius = params.get("dot_radius", 3.0)
        expansion_curve = params.get("expansion_curve", 0.7)
        drift_speed = params.get("drift_speed", 0.3)

        # Update drift
        self.drift_offset += drift_speed * 0.016
        self.drift_offset = self.drift_offset % (band.r_outer * 2)

        # Calculate vertical extent of the band
        vertical_extent = band.r_outer * 2
        dot_spacing_y = vertical_extent / (dots_per_col + 1)

        # Calculate horizontal positions for columns
        band_width = band.r_outer - band.r_inner
        col_spacing = band_width / (columns_per_side * 2)

        # Set up clipping
        painter.setClipPath(band.clip_path)

        # Draw left and right curtains
        for side in [-1, 1]:  # -1 = left, 1 = right
            for col in range(columns_per_side):
                # Calculate column radius (distance from center)
                col_radius = band.r_inner + col * col_spacing + col_spacing / 2

                # Calculate maximum brightness for this column
                # Inner columns light up at lower volumes
                distance_from_inner = col / max(1, columns_per_side - 1)
                activation_threshold = distance_from_inner**expansion_curve

                if audio.volume < activation_threshold:
                    column_brightness = 0.0
                else:
                    # Normalize brightness based on how much above threshold
                    column_brightness = (audio.volume - activation_threshold) / (
                        1 - activation_threshold
                    )
                    column_brightness = np.clip(column_brightness, 0.0, 1.0)

                if column_brightness < 0.01:
                    continue

                # Draw dots in this column
                for dot_idx in range(dots_per_col):
                    # Calculate vertical position with drift
                    y_base = -band.r_outer + (dot_idx + 1) * dot_spacing_y
                    y = y_base + self.drift_offset
                    # Wrap around for continuous drift
                    if y > band.r_outer:
                        y -= vertical_extent

                    # Calculate horizontal position (curved to follow donut)
                    # Only draw if within the band
                    if abs(y) > band.r_outer * 0.9:
                        continue

                    # Calculate x based on y to follow donut curvature
                    y_normalized = y / band.r_outer
                    x_offset = np.sqrt(max(0, 1 - y_normalized**2)) * col_radius
                    x = side * x_offset

                    # Check if point is within band
                    radius_at_y = np.sqrt(x**2 + y**2)
                    if radius_at_y < band.r_inner or radius_at_y > band.r_outer:
                        continue

                    # Calculate dot brightness with vertical gradient
                    # Dots at center are brighter
                    vertical_factor = 1 - abs(y) / band.r_outer * 0.3
                    dot_brightness = column_brightness * vertical_factor

                    # Color scheme
                    if audio.volume > 0.8:
                        color = QColor(255, int(200 * dot_brightness), 0)
                    elif audio.volume > 0.5:
                        color = QColor(
                            int(255 * dot_brightness),
                            255,
                            int(100 * (1 - dot_brightness)),
                        )
                    else:
                        color = QColor(
                            int(100 * dot_brightness),
                            int(200 + 55 * dot_brightness),
                            255,
                        )

                    color.setAlphaF(dot_brightness)
                    painter.setBrush(color)
                    painter.setPen(QColor(0, 0, 0, 0))

                    # Pulse size with brightness
                    current_radius = dot_radius * (0.6 + 0.4 * dot_brightness)

                    painter.drawEllipse(
                        QPointF(
                            band.center.x() + x - current_radius,
                            band.center.y() + y - current_radius,
                        ),
                        current_radius * 2,
                        current_radius * 2,
                    )
