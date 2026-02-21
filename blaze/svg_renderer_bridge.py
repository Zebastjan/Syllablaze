"""
SVG Renderer Bridge for QML

Exposes SVG element bounds to QML for precise positioning.
Uses QSvgRenderer to load the SVG and get element boundaries by ID.
"""

from PyQt6.QtCore import QObject, pyqtProperty, QRectF, QPointF
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPainter
import os
import logging

logger = logging.getLogger(__name__)


class SvgRendererBridge(QObject):
    """
    Bridge class that exposes SVG element bounds to QML.

    This allows QML to position overlays exactly on top of specific
    SVG elements by their IDs.
    """

    def __init__(self, svg_path=None, parent=None):
        super().__init__(parent)

        if svg_path is None:
            # Search for syllablaze.svg in multiple locations
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths = [
                # Development: resources/ at project root
                os.path.join(base_dir, "resources", "syllablaze.svg"),
                # Installed: resources/ in site-packages
                os.path.join(os.path.dirname(base_dir), "resources", "syllablaze.svg"),
                # System icons: where install.py copies it
                os.path.expanduser(
                    "~/.local/share/icons/hicolor/256x256/apps/syllablaze.svg"
                ),
            ]

            svg_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    svg_path = path
                    break

            if svg_path is None:
                logger.error(
                    f"Could not find syllablaze.svg in any of: {possible_paths}"
                )
                # Fallback to first path even though it doesn't exist
                svg_path = possible_paths[0]

        self._svg_path = svg_path
        self._renderer = QSvgRenderer(svg_path)

        if not self._renderer.isValid():
            logger.error(f"Failed to load SVG: {svg_path}")
        else:
            logger.info(f"SVG Renderer loaded: {svg_path}")

        # Cache element bounds
        self._background_bounds = None
        self._input_level_bounds = None
        self._waveform_bounds = None
        self._active_area_bounds = None
        self._view_box = self._renderer.viewBoxF()

        logger.info(f"SVG viewBox: {self._view_box}")

    @pyqtProperty(QRectF)
    def backgroundBounds(self):
        """Get the bounds of the background element"""
        if self._background_bounds is None:
            self._background_bounds = self._renderer.boundsOnElement("background")
            if self._background_bounds.isNull():
                logger.warning("background element not found in SVG, using fallback")
                self._background_bounds = QRectF(0, 0, 512, 512)
            else:
                logger.info(f"background bounds: {self._background_bounds}")
        return self._background_bounds

    @pyqtProperty(QRectF)
    def inputLevelBounds(self):
        """Get the bounds of the input_levels element for audio level overlay"""
        if self._input_level_bounds is None:
            self._input_level_bounds = self._renderer.boundsOnElement("input_levels")
            if self._input_level_bounds.isNull():
                logger.warning("input_levels element not found in SVG, using fallback")
                # Fallback to approximate center area
                self._input_level_bounds = QRectF(100, 100, 312, 312)
            else:
                logger.info(f"input_levels bounds: {self._input_level_bounds}")
        return self._input_level_bounds

    @pyqtProperty(QRectF)
    def waveformBounds(self):
        """Get the bounds of the waveform element"""
        if self._waveform_bounds is None:
            self._waveform_bounds = self._renderer.boundsOnElement("waveform")
            if self._waveform_bounds.isNull():
                logger.warning("waveform element not found in SVG, using fallback")
                # Fallback to approximate ring area
                self._waveform_bounds = QRectF(50, 50, 412, 412)
            else:
                logger.info(f"waveform bounds: {self._waveform_bounds}")
        return self._waveform_bounds

    @pyqtProperty(QRectF)
    def activeAreaBounds(self):
        """Get the bounds of the active_area element for click detection"""
        if self._active_area_bounds is None:
            self._active_area_bounds = self._renderer.boundsOnElement("active_area")
            if self._active_area_bounds.isNull():
                logger.warning("active_area element not found in SVG, using fallback")
                # Fallback to full window
                self._active_area_bounds = QRectF(0, 0, 512, 512)
            else:
                logger.info(f"active_area bounds: {self._active_area_bounds}")
        return self._active_area_bounds

    @pyqtProperty(QRectF)
    def viewBox(self):
        """Get the SVG viewBox"""
        return self._view_box

    @pyqtProperty(float)
    def viewBoxWidth(self):
        """Get SVG viewBox width"""
        return self._view_box.width()

    @pyqtProperty(float)
    def viewBoxHeight(self):
        """Get SVG viewBox height"""
        return self._view_box.height()

    @pyqtProperty(str)
    def svgPath(self):
        """Get the path to the loaded SVG file"""
        return self._svg_path

    def render(self, painter: QPainter):
        """Render the full SVG to the painter"""
        self._renderer.render(painter)

    def renderElement(self, painter: QPainter, element_id: str):
        """Render a specific element by ID"""
        self._renderer.render(painter, element_id)

    def mapSvgToWidget(
        self, svg_x: float, svg_y: float, widget_width: float, widget_height: float
    ) -> QPointF:
        """
        Map SVG coordinates to widget coordinates.

        Args:
            svg_x: X coordinate in SVG space
            svg_y: Y coordinate in SVG space
            widget_width: Target widget width
            widget_height: Target widget height

        Returns:
            QPointF in widget coordinates
        """
        scale_x = widget_width / self._view_box.width()
        scale_y = widget_height / self._view_box.height()

        widget_x = (svg_x - self._view_box.x()) * scale_x
        widget_y = (svg_y - self._view_box.y()) * scale_y

        return QPointF(widget_x, widget_y)

    def mapSvgRectToWidget(
        self, svg_rect: QRectF, widget_width: float, widget_height: float
    ) -> QRectF:
        """
        Map an SVG rectangle to widget coordinates.

        Args:
            svg_rect: QRectF in SVG coordinates
            widget_width: Target widget width
            widget_height: Target widget height

        Returns:
            QRectF in widget coordinates
        """
        top_left = self.mapSvgToWidget(
            svg_rect.x(), svg_rect.y(), widget_width, widget_height
        )
        bottom_right = self.mapSvgToWidget(
            svg_rect.x() + svg_rect.width(),
            svg_rect.y() + svg_rect.height(),
            widget_width,
            widget_height,
        )

        return QRectF(
            top_left.x(),
            top_left.y(),
            bottom_right.x() - top_left.x(),
            bottom_right.y() - top_left.y(),
        )
