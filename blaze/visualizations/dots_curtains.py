"""
DotsSideCurtains visualization pattern.
Vertical dot columns on left and right sides that expand from center to fill full window height.
"""

import numpy as np
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QColor
from .base import BandGeometry


class DotsSideCurtains:
    """Two vertical columns of dots that expand from center to full window height."""

    name = "dots_curtains"
    display_name = "Side Curtains"

    def __init__(self):
        self.drift_offset = 0.0  # For vertical drift animation

    def paint(self, painter: QPainter, band: BandGeometry, audio, params: dict) -> None:
        """Draw side curtain dot columns that expand from center to full height."""
        # Get parameters with defaults
        dots_per_col = params.get("dots_per_col", 60)  # More dots for full height
        max_columns = params.get("max_columns", 3)
        dot_radius = params.get("dot_radius", 4.0)
        drift_speed = params.get("drift_speed", 0.15)

        # Amplify volume for better visualization
        sensitivity = 0.002
        display_volume = min(1.0, audio.volume / sensitivity)
        # Ensure minimum visibility so there's always some activity
        display_volume = max(0.15, display_volume)

        # Update drift
        self.drift_offset += drift_speed * 0.016

        # Use FULL window height - from center to top/bottom edges
        # r_outer is the radius to the edge of the window
        # Expand by 25% to reach closer to the actual window edge
        full_height_radius = band.r_outer * 1.25
        band_center_y = band.center.y()
        band_center_x = band.center.x()

        # Column positions: start just outside the microphone icon (r_inner)
        # and work outward toward the window edge
        r_inner = band.r_inner
        base_offset = r_inner + dot_radius  # One dot width from icon edge
        column_spacing = dot_radius * 2.2  # Slightly more than diameter
        column_x_offsets = [
            base_offset + i * column_spacing for i in range(max_columns)
        ]

        # Calculate vertical spacing to fill from center to top/bottom
        # We want dots from -r_outer to +r_outer (full window diameter)
        usable_height = full_height_radius * 2  # Full diameter
        dot_spacing_y = (
            usable_height / (dots_per_col - 1) if dots_per_col > 1 else usable_height
        )

        # Calculate how many dots to show based on volume
        # Expand from center outward - at max volume, show dots to the full top and bottom
        expansion_factor = display_volume
        dots_visible_per_column = max(3, int(dots_per_col * expansion_factor))
        # Ensure odd number for perfect centering
        if dots_visible_per_column % 2 == 0:
            dots_visible_per_column += 1

        # Draw left and right curtains
        for side in [-1, 1]:  # -1 = left, 1 = right
            for col_idx in range(max_columns):
                # Get x position for this column
                x_offset = column_x_offsets[col_idx]
                x = side * x_offset

                # Brightness fades for outer columns
                column_brightness = 1.0 - (col_idx * 0.15)

                # Calculate center index for expansion
                center_idx = (dots_visible_per_column - 1) // 2

                for dot_idx in range(dots_visible_per_column):
                    # Calculate position from center outward
                    offset_from_center = dot_idx - center_idx

                    # Calculate y position with drift - full window height
                    y_raw = offset_from_center * dot_spacing_y + self.drift_offset

                    # Wrap drift to create continuous scrolling effect
                    while y_raw > usable_height / 2:
                        y_raw -= usable_height
                    while y_raw < -usable_height / 2:
                        y_raw += usable_height

                    # Only draw if within the circular window bounds
                    # Check if dot is within the circular window (r_outer)
                    actual_radius = np.sqrt(x_offset**2 + y_raw**2)
                    if actual_radius > full_height_radius - dot_radius * 0.5:
                        continue
                    # Also check it's outside the microphone icon (r_inner)
                    if actual_radius < r_inner - dot_radius:
                        continue

                    y = band_center_y + y_raw

                    # Brightness based on distance from center (center dots brightest)
                    distance_from_center_factor = (
                        1.0
                        - (abs(offset_from_center) / (dots_visible_per_column / 2))
                        * 0.3
                    )
                    dot_brightness = column_brightness * distance_from_center_factor
                    dot_brightness = max(0.4, min(1.0, dot_brightness))

                    # Color based on volume - vibrant colors
                    if display_volume > 0.7:
                        color = QColor(255, int(200 * dot_brightness), 0)  # Orange
                    elif display_volume > 0.4:
                        color = QColor(
                            int(255 * dot_brightness),
                            255,
                            int(100 * (1 - dot_brightness)),
                        )  # Yellow-green
                    else:
                        color = QColor(
                            int(100 * dot_brightness),
                            int(200 + 55 * dot_brightness),
                            255,
                        )  # Blue

                    color.setAlphaF(dot_brightness)
                    painter.setBrush(color)
                    painter.setPen(QColor(0, 0, 0, 0))

                    # Draw the dot
                    painter.drawEllipse(
                        QPointF(band_center_x + x, y),
                        dot_radius,
                        dot_radius,
                    )

    applet_defaults = {
        "dots_curtains": {
            "dots_per_col": 60,  # More dots for full window height
            "max_columns": 3,
            "dot_radius": 4.0,
            "drift_speed": 0.15,
        },
    }
