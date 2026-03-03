"""
Main window for visualization test app.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer

from patterns import get_pattern, get_next_pattern
from patterns.base import BandGeometry
from audio_generator import WaveformGenerator
from config import ConfigManager


class VisualizationWindow(QWidget):
    """Frameless window that renders SVG with visualization overlay."""

    def __init__(self, config: ConfigManager):
        super().__init__()

        self.config = config
        self.waveform_generator = WaveformGenerator()
        self.audio_state = None

        # Window setup
        self.setWindowTitle("Syllablaze Visualization Test")
        self.resize(200, 200)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Load SVG
        svg_path = Path(__file__).parent.parent.parent / "resources" / "syllablaze.svg"
        self.svg_renderer = QSvgRenderer(str(svg_path))

        # Get SVG size
        self.svg_size = self.svg_renderer.defaultSize()

        # Current pattern
        self.current_pattern_instance = None
        self._load_pattern()

        # Animation timer (~60 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(16)  # ~60 FPS

        # Connect config reload
        self.config.config_changed.connect(self._on_config_changed)

        # Start playing by default
        self.waveform_generator.toggle_playback()

        print("Visualization Test App Started!")
        print(f"  Left-click: Play/Pause")
        print(f"  Middle-click: Switch pattern ({self.config.current_pattern})")
        print(f"  Right-click: Open config in helix")
        print(f"  Scroll: Resize window")

    def _load_pattern(self):
        """Load current pattern from config."""
        pattern_name = self.config.current_pattern
        try:
            self.current_pattern_instance = get_pattern(pattern_name)
            print(f"Loaded pattern: {self.current_pattern_instance.display_name}")
        except ValueError as e:
            print(f"Error loading pattern: {e}")
            self.current_pattern_instance = get_pattern("dots_radial")

    def _on_config_changed(self):
        """Handle config reload."""
        self._load_pattern()
        self.update()

    def _update_frame(self):
        """Update animation frame."""
        self.audio_state = self.waveform_generator.update()
        self.update()

    def paintEvent(self, event):
        """Paint SVG and visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate scale to fit in current window size
        scale = min(
            self.width() / self.svg_size.width(), self.height() / self.svg_size.height()
        )

        # Calculate centering offset
        offset_x = (self.width() - self.svg_size.width() * scale) / 2
        offset_y = (self.height() - self.svg_size.height() * scale) / 2

        painter.translate(offset_x, offset_y)
        painter.scale(scale, scale)

        # Render SVG
        self.svg_renderer.render(painter)

        # Draw visualization if we have audio state
        if self.audio_state and self.current_pattern_instance:
            self._draw_visualization(painter)

        # Draw play/pause indicator
        self._draw_indicator(painter)

    def _draw_visualization(self, painter: QPainter):
        """Draw the visualization pattern in the donut band."""
        # Calculate band geometry based on current painter transformation
        # The SVG viewBox is 512x512, so we calculate proportional to that
        svg_center_x = 256.0
        svg_center_y = 256.0
        svg_size = 512.0

        # The waveform donut is typically centered at (256, 256) with outer radius ~200-220
        # We want the visualization to fill the donut band between inner and outer edges
        center = QPointF(svg_center_x, svg_center_y)
        r_outer = 210.0  # Approximate outer radius in SVG coordinates
        r_inner = 130.0  # Approximate inner radius in SVG coordinates (leaves room for mic icon)

        # Create donut clip path in SVG coordinates
        clip_path = QPainterPath()
        clip_path.addEllipse(center, r_outer, r_outer)
        inner_path = QPainterPath()
        inner_path.addEllipse(center, r_inner, r_inner)
        clip_path = clip_path.subtracted(inner_path)

        band = BandGeometry(
            center=center, r_inner=r_inner, r_outer=r_outer, clip_path=clip_path
        )

        # Get pattern parameters
        params = self.config.get_pattern_params()

        # Paint the pattern
        self.current_pattern_instance.paint(painter, band, self.audio_state, params)

    def _draw_indicator(self, painter: QPainter):
        """Draw play/pause indicator and pattern name."""
        # Reset transform to draw in window coordinates
        painter.resetTransform()

        # Draw indicator dot in top-right corner
        indicator_color = (
            QColor(0, 255, 0)
            if self.waveform_generator.is_playing
            else QColor(255, 0, 0)
        )
        painter.setBrush(indicator_color)
        painter.setPen(QColor(0, 0, 0, 0))
        dot_x = self.width() - 20
        dot_y = 10
        painter.drawEllipse(dot_x, dot_y, 10, 10)

        # Draw pattern name at bottom-left
        if self.current_pattern_instance:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Sans", max(6, self.width() // 25))
            font.setBold(True)
            painter.setFont(font)
            text_y = self.height() - 10
            painter.drawText(10, text_y, self.current_pattern_instance.display_name)

    def mousePressEvent(self, event):
        """Handle mouse clicks."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Play/Pause
            is_playing = self.waveform_generator.toggle_playback()
            print(f"{'Playing' if is_playing else 'Paused'}")
            self.update()

        elif event.button() == Qt.MouseButton.MiddleButton:
            # Switch pattern
            current = self.config.current_pattern
            next_pattern = get_next_pattern(current)
            self.config.current_pattern = next_pattern
            self._load_pattern()
            print(f"Switched to: {self.current_pattern_instance.display_name}")
            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            # Open config in helix
            print("Opening config in helix...")
            self.config.open_in_editor()

    def mouseMoveEvent(self, event):
        """Enable window dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.rect().center())

    def wheelEvent(self, event):
        """Handle scroll wheel to resize window, keeping it centered."""
        # Get current center before resize
        center = self.geometry().center()

        # Calculate size change (10px per scroll click)
        delta = event.angleDelta().y() / 120  # 1 click = 15 degrees = 120 units
        new_size = self.width() + int(delta * 10)

        # Clamp to valid range (100-500px)
        new_size = max(100, min(500, new_size))

        # Resize
        self.resize(new_size, new_size)

        # Move to keep centered on same point
        new_geo = self.geometry()
        new_geo.moveCenter(center)
        self.setGeometry(new_geo)

        self.update()
