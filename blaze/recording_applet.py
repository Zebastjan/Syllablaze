"""
Recording Applet - Plain QWidget implementation for Syllablaze

This is a frameless, circular applet that displays recording state and volume visualization.
Replaces the QML-based RecordingDialog for better Wayland/KWin compatibility.
"""

import os
import logging
from collections import deque

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QRectF,
    pyqtSignal,
)
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QCursor

logger = logging.getLogger(__name__)


class RecordingApplet(QWidget):
    """Recording applet - a circular, frameless widget for recording state visualization."""

    # Signals for user actions
    toggleRecordingRequested = pyqtSignal()
    openClipboardRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()
    dismissRequested = pyqtSignal()
    windowPositionChanged = pyqtSignal(int, int)
    windowSizeChanged = pyqtSignal(int)

    def __init__(self, settings, app_state, audio_manager=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.app_state = app_state
        self.audio_manager = audio_manager

        # State
        self._is_recording = False
        self._is_transcribing = False
        self._current_volume = 0.0
        self._audio_samples = deque(maxlen=128)

        # Mouse state
        self._drag_position = None
        self._was_dragged = False
        self._click_timer = None
        self._is_double_click_sequence = False

        # Position save debounce
        self._position_save_timer = QTimer()
        self._position_save_timer.setSingleShot(True)
        self._position_save_timer.timeout.connect(self._save_position)

        # Click ignore after show
        self._show_ignore_timer = QTimer()
        self._show_ignore_timer.setSingleShot(True)
        self._show_ignore_timer.timeout.connect(self._enable_clicks)
        self._ignore_clicks = True

        # SVG renderer
        self._svg_renderer = None
        self._svg_viewbox = QRectF(0, 0, 512, 512)
        self._background_bounds = QRectF()
        self._waveform_bounds = QRectF()
        self._active_area_bounds = QRectF()

        # Load SVG
        self._load_svg()

        # Setup window
        self._setup_window()

        # Build context menu
        self._build_context_menu()

        # Connect to app state
        self._connect_signals()

        # Initial size - start at 200x200 like QML version
        self.resize(200, 200)

    def _load_svg(self):
        """Load the syllablaze.svg and extract element bounds."""
        from PyQt6.QtSvg import QSvgRenderer

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths = [
            os.path.join(base_dir, "resources", "syllablaze.svg"),
            os.path.expanduser(
                "~/.local/share/icons/hicolor/256x256/apps/syllablaze.svg"
            ),
        ]

        svg_path = None
        for path in possible_paths:
            if os.path.exists(path):
                svg_path = path
                break

        if not svg_path:
            logger.error("Could not find syllablaze.svg")
            return

        self._svg_renderer = QSvgRenderer(svg_path)
        if not self._svg_renderer.isValid():
            logger.error(f"Failed to load SVG: {svg_path}")
            return

        logger.info(f"RecordingApplet: Loaded SVG from {svg_path}")
        self._svg_viewbox = self._svg_renderer.viewBoxF()

        # Get element bounds
        self._background_bounds = self._svg_renderer.boundsOnElement("background")
        if self._background_bounds.isNull():
            self._background_bounds = QRectF(0, 0, 512, 512)

        self._waveform_bounds = self._svg_renderer.boundsOnElement("waveform")
        if self._waveform_bounds.isNull():
            # Fallback: approximate ring area
            self._waveform_bounds = QRectF(50, 50, 412, 412)

        self._active_area_bounds = self._svg_renderer.boundsOnElement("active_area")
        if self._active_area_bounds.isNull():
            # Fallback: full window
            self._active_area_bounds = QRectF(0, 0, 512, 512)

    def _setup_window(self):
        """Configure window flags and properties.

        Note: We use KWin window rules for always-on-top and on-all-desktops.
        Qt window hints are unreliable on Wayland - KWin is the proper way.
        """
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        # Base flags: frameless tool window (no window hints for properties)
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        self.setWindowFlags(flags)

        # Set window title so KWin rules can target it
        self.setWindowTitle("Syllablaze Recording")

    def _build_context_menu(self):
        """Build the right-click context menu."""
        self._context_menu = QMenu(self)

        self._toggle_action = self._context_menu.addAction("Start Recording")
        self._toggle_action.triggered.connect(self._on_toggle_clicked)

        self._context_menu.addAction("Open Clipboard").triggered.connect(
            self.openClipboardRequested.emit
        )
        self._context_menu.addAction("Settings").triggered.connect(
            self.openSettingsRequested.emit
        )

        self._context_menu.addSeparator()

        self._context_menu.addAction("Dismiss").triggered.connect(
            self._on_dismiss_clicked
        )

    def _connect_signals(self):
        """Connect to ApplicationState signals."""
        if self.app_state:
            self.app_state.recording_state_changed.connect(
                self._on_recording_state_changed
            )
            self.app_state.transcription_state_changed.connect(
                self._on_transcribing_state_changed
            )

        # Connect to audio manager for volume
        if self.audio_manager:
            self.audio_manager.volume_changing.connect(self._on_volume_changed)
            self.audio_manager.audio_samples_changing.connect(self._on_samples_changed)

    def _on_recording_state_changed(self, is_recording):
        """Handle recording state change."""
        self._is_recording = is_recording

        # Update menu text
        self._toggle_action.setText(
            "Stop Recording" if is_recording else "Start Recording"
        )

        # Trigger repaint to show/hide recording visuals
        self.update()

    def _on_transcribing_state_changed(self, is_transcribing):
        """Handle transcription state change."""
        self._is_transcribing = is_transcribing
        self.update()

    def _on_volume_changed(self, volume):
        """Handle volume update from AudioManager."""
        self._current_volume = max(0.0, min(1.0, volume))
        self.update()

    def _on_samples_changed(self, samples):
        """Handle audio samples update."""
        if samples:
            self._audio_samples = deque(samples[-128:], maxlen=128)


    def paintEvent(self, event):
        """Custom painting for the recording applet."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw circular clipping path
        painter.save()
        path = QPainterPath()
        path.addEllipse(0, 0, width, height)
        painter.setClipPath(path)

        # Render the entire SVG scaled to widget size
        if self._svg_renderer and self._svg_renderer.isValid():
            # The SVG renderer will handle rendering all visible elements
            # The waveform and active_area are transparent regions used for logic
            target_rect = QRectF(0, 0, width, height)
            self._svg_renderer.render(painter, target_rect)

        # Volume visualization overlay (only when recording)
        if self._is_recording:
            self._paint_volume_visualization(painter)

        # Transcription overlay
        if self._is_transcribing:
            overlay_color = QColor(0, 0, 0, 150)
            painter.fillRect(0, 0, width, height, overlay_color)

            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, "Transcribing..."
            )

        painter.restore()

    def _paint_volume_visualization(self, painter):
        """Paint the radial volume visualization over the waveform region."""
        # Map waveform bounds from SVG coordinates to widget coordinates
        waveform_widget = self._map_svg_rect_to_widget(self._waveform_bounds)

        # Calculate center and ring dimensions from mapped waveform bounds
        center_x = waveform_widget.x() + waveform_widget.width() / 2
        center_y = waveform_widget.y() + waveform_widget.height() / 2
        inner_radius = min(waveform_widget.width(), waveform_widget.height()) * 0.35
        outer_radius = min(waveform_widget.width(), waveform_widget.height()) * 0.48

        # Draw radial waveform bars if we have samples
        if self._audio_samples and len(self._audio_samples) > 0:
            self._paint_radial_waveform(
                painter, center_x, center_y, inner_radius, outer_radius
            )
        else:
            # Fallback: draw a simple pulsing ring
            viz_radius = inner_radius + (self._current_volume * (outer_radius - inner_radius))

            # Color based on volume level
            if self._current_volume < 0.6:
                color = QColor(0, 200, 0, int(150 + self._current_volume * 100))
            elif self._current_volume < 0.85:
                color = QColor(255, 180, 0, int(180 + self._current_volume * 75))
            else:
                color = QColor(255, 50, 0, int(200 + self._current_volume * 50))

            pen = QPen(color, 2 + self._current_volume * 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(
                QPoint(int(center_x), int(center_y)),
                int(viz_radius),
                int(viz_radius)
            )

    def _paint_radial_waveform(self, painter, cx, cy, inner_radius, outer_radius):
        """Paint radial waveform bars based on audio samples."""
        import math

        num_bars = 36  # Match QML version
        ring_thickness = outer_radius - inner_radius - 4

        painter.save()

        for i in range(num_bars):
            # Calculate angle for this bar (start at top: -π/2)
            angle = (i / num_bars) * 2 * math.pi - (math.pi / 2)

            # Get corresponding audio sample
            sample_index = int((i / num_bars) * len(self._audio_samples))
            raw_sample = abs(self._audio_samples[sample_index]) if sample_index < len(self._audio_samples) else 0

            # Amplify sample for visualization (input is often very quiet)
            sample = min(1.0, raw_sample * 10)

            # Calculate bar length with minimum visible length
            min_length = 5
            max_length = ring_thickness * 0.8
            bar_length = min_length + (sample * max_length)

            # Calculate color based on sample value
            if sample < 0.5:
                # Green to yellow-green
                t = sample * 2
                r = int((0.2 + t * 0.8) * 255)
                g = int(0.8 * 255)
                b = int(0.2 * 255)
            else:
                # Yellow-green to red
                t = (sample - 0.5) * 2
                r = int(1.0 * 255)
                g = int((0.8 - t * 0.8) * 255)
                b = int(0.2 * 255)

            color = QColor(r, g, b, 230)  # 0.9 alpha = 230

            # Draw the bar
            pen = QPen(color, 3)
            painter.setPen(pen)

            # Start point at inner radius
            start_x = cx + math.cos(angle) * inner_radius
            start_y = cy + math.sin(angle) * inner_radius

            # End point at inner_radius + bar_length
            end_x = cx + math.cos(angle) * (inner_radius + bar_length)
            end_y = cy + math.sin(angle) * (inner_radius + bar_length)

            painter.drawLine(
                int(start_x), int(start_y),
                int(end_x), int(end_y)
            )

        painter.restore()


    def _map_svg_rect_to_widget(self, svg_rect):
        """Map SVG coordinates to widget coordinates."""
        scale = self.width() / self._svg_viewbox.width()
        return QRectF(
            svg_rect.x() * scale,
            svg_rect.y() * scale,
            svg_rect.width() * scale,
            svg_rect.height() * scale,
        )

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if self._ignore_clicks:
            return

        self._drag_position = event.globalPosition().toPoint()
        self._was_dragged = False

        # Check for double-click sequence
        if event.button() == Qt.MouseButton.LeftButton:
            if self._click_timer and self._click_timer.isActive():
                self._click_timer.stop()
                self._is_double_click_sequence = True

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self._ignore_clicks:
            return

        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._drag_position:
                delta = event.globalPosition().toPoint() - self._drag_position
                if delta.manhattanLength() > 5:
                    # Use Qt's system move for proper Wayland/X11 dragging
                    if not self._was_dragged and self.windowHandle():
                        self.windowHandle().startSystemMove()
                        self._was_dragged = True
                        return
                    self._drag_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for clicks."""
        if self._ignore_clicks:
            self._drag_position = None
            return

        if self._was_dragged:
            # Drag completed - save position after delay
            self._position_save_timer.start(500)
            self._was_dragged = False
        elif event.button() == Qt.MouseButton.LeftButton:
            if self._is_double_click_sequence:
                # Double-click: dismiss
                self._is_double_click_sequence = False
                self._on_double_click()
            else:
                # Start click timer for single-click detection
                self._click_timer = QTimer(self)
                self._click_timer.setSingleShot(True)
                self._click_timer.timeout.connect(self._on_single_click)
                self._click_timer.start(250)
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Middle-click: open clipboard
            self.openClipboardRequested.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            # Right-click: show context menu
            self._context_menu.exec(QCursor.pos())

        self._drag_position = None

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to dismiss."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_double_click()

    def wheelEvent(self, event):
        """Handle scroll wheel for resizing."""
        delta = event.angleDelta().y()
        size_change = 20 if delta > 0 else -20

        new_size = max(100, min(500, self.width() + size_change))
        self.resize(new_size, new_size)

        self.windowSizeChanged.emit(new_size)
        logger.info(f"RecordingApplet: Resized via scroll to {new_size}x{new_size}")

    def _on_single_click(self):
        """Handle single click - toggle recording."""
        if not self._ignore_clicks:
            self._on_toggle_clicked()

    def _on_double_click(self):
        """Handle double-click - dismiss."""
        self._save_position()
        self.dismissRequested.emit()

    def _on_toggle_clicked(self):
        """Handle toggle recording action."""
        self.toggleRecordingRequested.emit()

    def _on_dismiss_clicked(self):
        """Handle dismiss action."""
        self._save_position()
        self.dismissRequested.emit()

    def _save_position(self):
        """Save current position to settings."""
        if self.x() != 0 or self.y() != 0:
            self.windowPositionChanged.emit(self.x(), self.y())
            logger.info(f"RecordingApplet: Saved position ({self.x()}, {self.y()})")

    def _enable_clicks(self):
        """Re-enable click handling after show delay."""
        self._ignore_clicks = False

    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        # Ignore clicks for 300ms after showing
        self._ignore_clicks = True
        self._show_ignore_timer.start(300)

        # Apply window properties via KWin on first show
        if not hasattr(self, '_properties_applied'):
            self._properties_applied = False

        if not self._properties_applied:
            # Use QTimer to ensure window is fully mapped before applying KWin properties
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._apply_kwin_properties)

    def _apply_kwin_properties(self):
        """Apply window properties via KWin (called after window is shown)."""
        from . import kwin_rules

        # Mark as applied
        self._properties_applied = True

        always_on_top = self.settings.get("recording_dialog_always_on_top", True)
        applet_mode = self.settings.get("applet_mode", "popup")
        on_all = self.settings.get("applet_onalldesktops", True)

        # Only apply on-all-desktops in persistent mode
        on_all_value = on_all if applet_mode == "persistent" else False

        logger.info(
            f"RecordingApplet: Applying KWin properties - "
            f"always_on_top={always_on_top}, on_all_desktops={on_all_value}, mode={applet_mode}"
        )

        # Update KWin rule
        kwin_rules.create_or_update_kwin_rule(
            enable_keep_above=always_on_top,
            on_all_desktops=on_all_value
        )

        # Apply on-all-desktops immediately via D-Bus
        if applet_mode == "persistent":
            kwin_rules.set_window_on_all_desktops("Syllablaze Recording", on_all_value)

    def requestActivate(self):
        """Request window activation."""
        if self.windowHandle():
            self.windowHandle().requestActivate()
        else:
            self.activateWindow()

    def set_on_all_desktops(self, on_all: bool):
        """Set whether window appears on all desktops via KWin.

        Uses KWin scripting D-Bus API to set the property on the running window,
        and also updates the KWin rule for persistence.
        """
        from . import kwin_rules

        logger.info(f"RecordingApplet: set_on_all_desktops({on_all})")

        always_on_top = self.settings.get("recording_dialog_always_on_top", True)

        # Update the KWin rule for persistence
        kwin_rules.create_or_update_kwin_rule(
            enable_keep_above=always_on_top,
            on_all_desktops=on_all
        )

        # Apply to the current window via KWin D-Bus (works immediately)
        kwin_rules.set_window_on_all_desktops("Syllablaze Recording", on_all)

    def set_always_on_top(self, always_on_top: bool):
        """Update always-on-top setting via KWin.

        Uses KWin window rules instead of Qt window hints (Wayland-friendly).
        """
        from . import kwin_rules

        logger.info(f"RecordingApplet: set_always_on_top({always_on_top})")

        on_all = self.settings.get("applet_onalldesktops", True)
        applet_mode = self.settings.get("applet_mode", "popup")

        # Only apply on-all-desktops in persistent mode
        on_all_value = on_all if applet_mode == "persistent" else False

        # Update KWin rule with new always-on-top setting
        kwin_rules.create_or_update_kwin_rule(
            enable_keep_above=always_on_top,
            on_all_desktops=on_all_value
        )

    def update_always_on_top_setting(self, always_on_top: bool):
        """Update always-on-top from settings."""
        self.set_always_on_top(always_on_top)

    def set_recording_state(self, is_recording: bool):
        """Programmatically set recording state (for external control)."""
        # This just updates our local state tracking
        # The actual state is managed by ApplicationState
        self._on_recording_state_changed(is_recording)

    def set_transcribing_state(self, is_transcribing: bool):
        """Programmatically set transcribing state."""
        self._on_transcribing_state_changed(is_transcribing)

    # Properties for external access
    @property
    def is_recording(self):
        return self._is_recording

    @property
    def is_transcribing(self):
        return self._is_transcribing

    @property
    def current_volume(self):
        return self._current_volume
