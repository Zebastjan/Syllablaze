"""
Recording Applet - Plain QWidget implementation for Syllablaze

This is a frameless, circular applet that displays recording state and volume visualization.
Replaces the QML-based RecordingDialog for better Wayland/KWin compatibility.
"""

import os
import logging
import time
from collections import deque

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    QRectF,
    QPointF,
    pyqtSignal,
)
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QCursor, QActionGroup

# Import visualization patterns
from .visualizations import get_pattern, PATTERNS, PATTERN_ORDER
from .visualizations.base import AudioState, BandGeometry

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
    
    # Signals for volume/audio updates (for bridge to QML)
    volumeChanged = pyqtSignal(float)
    audioSamplesChanged = pyqtSignal(list)

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
        self._volume_history = deque(maxlen=64)  # For patterns that need history

        # Visualization
        self._current_pattern_name = self.settings.get("applet_visualization", "dots_radial")  # Load from settings
        self._current_pattern = None
        self._audio_state = None
        self._last_update_time = time.time()
        self._pattern_actions = []  # Store pattern menu actions for radio button behavior

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

        # Animation timer for smooth visualization (60fps)
        self._animation_timer = QTimer()
        self._animation_timer.setInterval(16)  # ~60fps
        self._animation_timer.timeout.connect(self.update)

        # SVG renderer
        self._svg_renderer = None
        self._svg_viewbox = QRectF(0, 0, 512, 512)
        self._background_bounds = QRectF()
        self._waveform_bounds = QRectF()
        self._active_area_bounds = QRectF()
        self._mic_group_bounds = QRectF()  # For inner radius calculation

        # Load SVG
        self._load_svg()

        # Setup window
        self._setup_window()

        # Build context menu
        self._build_context_menu()

        # Connect to app state
        self._connect_signals()

        # Initial size - start at active_area size (tight around icon)
        self._resize_to_state(False)

    def _load_visualization_pattern(self):
        """Load the current visualization pattern."""
        try:
            self._current_pattern = get_pattern(self._current_pattern_name)
            logger.info(f"Loaded visualization pattern: {self._current_pattern.display_name}")
        except ValueError as e:
            logger.warning(f"Failed to load pattern '{self._current_pattern_name}': {e}")
            # Fallback to dots_radial
            self._current_pattern_name = "dots_radial"
            self._current_pattern = get_pattern(self._current_pattern_name)

    def _resize_to_state(self, is_recording: bool):
        """Resize window based on recording state."""
        if is_recording:
            target_bounds = self._waveform_bounds
        else:
            target_bounds = self._active_area_bounds

        # Map SVG bounds to widget coordinates - use the larger dimension to maintain square
        target_widget = self._map_svg_rect_to_widget(target_bounds)
        
        # Ensure square aspect ratio (use larger dimension to avoid distortion)
        size = max(target_widget.width(), target_widget.height())
        
        # Keep window centered on current position
        current_center = self.geometry().center()
        
        # Create square rect centered at current position
        from PyQt6.QtCore import QRect
        target_rect = QRect(0, 0, int(size), int(size))
        target_rect.moveCenter(current_center)
        
        # Apply new geometry
        self.setGeometry(target_rect)
        
        logger.info(f"Resized to {'recording' if is_recording else 'idle'} state: {size}x{size}")

    def _get_band_geometry(self, window_width: int, window_height: int) -> BandGeometry:
        """Calculate the donut band geometry for visualization outside the icon."""
        # Use window center
        center = QPointF(window_width / 2, window_height / 2)
        
        # Inner radius is the outer edge of the icon (use waveform bounds)
        waveform_widget = self._map_svg_rect_to_widget(self._waveform_bounds)
        r_inner = min(waveform_widget.width(), waveform_widget.height()) / 2.0
        
        # Outer radius extends to the edge of the window
        r_outer = min(window_width, window_height) / 2.0 - 2  # Small margin
        
        # Create donut clip path (area outside icon but within window)
        clip_path = QPainterPath()
        clip_path.addEllipse(center, r_outer, r_outer)
        inner_path = QPainterPath()
        inner_path.addEllipse(center, r_inner, r_inner)
        clip_path = clip_path.subtracted(inner_path)
        
        return BandGeometry(
            center=center,
            r_inner=r_inner,
            r_outer=r_outer,
            clip_path=clip_path
        )

    def _create_audio_state(self) -> AudioState:
        """Create current audio state for visualization."""
        current_time = time.time()
        
        # Update volume history
        self._volume_history.append(self._current_volume)
        
        # Calculate recent peak
        recent_peak = max(self._volume_history) if self._volume_history else self._current_volume
        
        # Use audio samples for waveform visualization (like QML does)
        # If no samples yet, fall back to volume history
        if self._audio_samples:
            sample_history = self._audio_samples.copy()
        else:
            sample_history = self._volume_history.copy()
        
        logger.debug(f"Audio state: volume={self._current_volume:.3f}, samples={len(sample_history)}")
        
        return AudioState(
            volume=self._current_volume,
            history=sample_history,
            peak=recent_peak,
            time_s=current_time
        )

    def _get_pattern_params(self) -> dict:
        """Get parameters for the current pattern from settings."""
        # For now, return defaults. Later this can be enhanced with user settings.
        defaults = {
            'dots_radial': {
                'dot_spacing': 8,
                'dot_radius': 2.5,
                'wave_falloff': 1.5,
                'speed_min': 0.5,
                'speed_max': 4.0,
                'bounce': True,
            },
            'dots_curtains': {
                'dots_per_col': 20,
                'max_columns': 3,
                'dot_radius': 2.0,
                'drift_speed': 0.15,
            },
            'dots_radar': {
                'num_dots': 40,
                'dot_radius': 2.5,
                'trail_length': 3.14159 / 3,
                'speed_min': 0.2,
                'speed_max': 6.0,
                'num_rings': 1,
            },
        }
        
        return defaults.get(self._current_pattern_name, {})

    def set_visualization_pattern(self, pattern_name: str):
        """Set the visualization pattern."""
        if pattern_name in PATTERNS:
            self._current_pattern_name = pattern_name
            self.settings.set('applet_visualization', pattern_name)  # Save to settings
            self._load_visualization_pattern()
            self.update()
            logger.info(f"Changed visualization pattern to: {pattern_name}")
        else:
            logger.warning(f"Unknown pattern: {pattern_name}")

    def get_next_pattern(self) -> str:
        """Get the next pattern for cycling."""
        current_index = PATTERN_ORDER.index(self._current_pattern_name)
        next_index = (current_index + 1) % len(PATTERN_ORDER)
        return PATTERN_ORDER[next_index]

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

        # Get mic group bounds for inner radius calculation
        self._mic_group_bounds = self._svg_renderer.boundsOnElement("g3")
        if self._mic_group_bounds.isNull():
            # Fallback: estimate based on typical mic size
            self._mic_group_bounds = QRectF(150, 150, 212, 212)

        # Load initial visualization pattern
        self._load_visualization_pattern()

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
        
        # Add pattern cycling submenu with radio button behavior
        pattern_menu = self._context_menu.addMenu("Visualization")
        self._pattern_action_group = QActionGroup(self)  # For radio button exclusivity
        self._pattern_action_group.setExclusive(True)
        
        for pattern_name in PATTERN_ORDER:
            pattern_instance = get_pattern(pattern_name)
            action = pattern_menu.addAction(pattern_instance.display_name)
            action.setCheckable(True)
            action.setActionGroup(self._pattern_action_group)  # Add to group for exclusivity
            action.setChecked(pattern_name == self._current_pattern_name)
            action.triggered.connect(lambda checked, pn=pattern_name: self.set_visualization_pattern(pn))
            self._pattern_actions.append(action)

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
            logger.info(f"RecordingApplet: Connecting to audio_manager signals")
            self.audio_manager.volume_changing.connect(self._on_volume_changed)
            self.audio_manager.audio_samples_changing.connect(self._on_samples_changed)
            logger.info(f"RecordingApplet: Connected to audio_manager volume_changing and audio_samples_changing")
        else:
            logger.warning("RecordingApplet: No audio_manager provided, cannot connect volume signals")

    def _on_recording_state_changed(self, is_recording):
        """Handle recording state change."""
        self._is_recording = is_recording

        # Update menu text
        self._toggle_action.setText(
            "Stop Recording" if is_recording else "Start Recording"
        )

        # Resize window based on state
        self._resize_to_state(is_recording)

        # Start/stop animation timer for smooth visualization
        if is_recording:
            self._animation_timer.start()
        else:
            self._animation_timer.stop()

        # Trigger repaint to show/hide recording visuals
        self.update()

    def _on_transcribing_state_changed(self, is_transcribing):
        """Handle transcription state change."""
        self._is_transcribing = is_transcribing
        self.update()

    def _on_volume_changed(self, volume):
        """Handle volume update from AudioManager."""
        self._current_volume = max(0.0, min(1.0, volume))
        # Emit signal for bridge to QML
        self.volumeChanged.emit(self._current_volume)
        # Use INFO level when recording to see volume updates in normal logs
        if self._is_recording:
            logger.info(f"RecordingApplet: Volume={self._current_volume:.4f} during recording")
            logger.info(f"RecordingApplet: Volume update signal emitted")
        self.update()

    def _on_samples_changed(self, samples):
        """Handle audio samples update."""
        if samples:
            self._audio_samples = deque(samples[-128:], maxlen=128)
            # Emit signal for bridge to QML (convert deque to list)
            self.audioSamplesChanged.emit(list(self._audio_samples))
            logger.debug(f"RecordingApplet: Received {len(samples)} samples, stored {len(self._audio_samples)}")
        else:
            logger.debug("RecordingApplet: Received empty samples")


    def paintEvent(self, event):
        """Custom painting for the recording applet."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Clip to circular window shape
        painter.save()
        circular_clip = QPainterPath()
        circular_clip.addEllipse(0, 0, width, height)
        painter.setClipPath(circular_clip)

        # STEP 1: Render full SVG (preserves complete icon appearance)
        if self._svg_renderer and self._svg_renderer.isValid():
            target_rect = QRectF(0, 0, width, height)
            self._svg_renderer.render(painter, target_rect)

        # STEP 2: Draw visualization outside the icon (from perimeter outward)
        if self._is_recording and self._current_pattern:
            band = self._get_band_geometry(width, height)
            audio_state = self._create_audio_state()
            
            logger.debug(f"Painting pattern: {self._current_pattern_name}, widget={width}x{height}, band: center=({band.center.x():.1f}, {band.center.y():.1f}), r_inner={band.r_inner:.1f}, r_outer={band.r_outer:.1f}")
            
            # Clip to area outside icon but within window
            painter.save()
            painter.setClipPath(band.clip_path, Qt.ClipOperation.IntersectClip)
            
            # Paint the selected pattern
            params = self._get_pattern_params()
            self._current_pattern.paint(painter, band, audio_state, params)
            
            painter.restore()

        painter.restore()  # Remove circular clipping

        # Transcription overlay (drawn outside clipping)
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


    def _paint_simple_waveform(self, painter, band, audio):
        """Paint simple radial bars in the waveform ring - reliable and visible."""
        import math
        
        num_bars = 36
        band_width = band.r_outer - band.r_inner
        
        # Get volume (ensure it's in valid range)
        volume = max(0.0, min(1.0, audio.volume))
        
        # Draw bars around the ring
        for i in range(num_bars):
            angle = (i / num_bars) * 2 * math.pi - (math.pi / 2)
            
            # Start at inner radius
            start_x = band.center.x() + math.cos(angle) * band.r_inner
            start_y = band.center.y() + math.sin(angle) * band.r_inner
            
            # End based on volume
            bar_length = band_width * volume
            end_radius = band.r_inner + bar_length
            end_x = band.center.x() + math.cos(angle) * end_radius
            end_y = band.center.y() + math.sin(angle) * end_radius
            
            # Color based on volume - bright and visible
            if volume < 0.5:
                color = QColor(0, 255, 100, 230)  # Green
            elif volume < 0.8:
                color = QColor(255, 255, 0, 230)  # Yellow
            else:
                color = QColor(255, 50, 50, 230)  # Red
            
            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
        
        logger.debug(f"Drew {num_bars} bars with volume={volume:.3f}")

    def _map_svg_rect_to_widget(self, svg_rect):
        """Map SVG coordinates to widget coordinates."""
        scale = self.width() / self._svg_viewbox.width()
        return QRectF(
            svg_rect.x() * scale,
            svg_rect.y() * scale,
            svg_rect.width() * scale,
            svg_rect.height() * scale,
        )

    def _is_point_in_active_area(self, point: QPointF) -> bool:
        """Check if a point is within the active area bounds."""
        active_area_widget = self._map_svg_rect_to_widget(self._active_area_bounds)
        return active_area_widget.contains(point)

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if self._ignore_clicks:
            return

        # Check if click is within active area (visible region)
        if not self._is_point_in_active_area(event.position()):
            # Click is in transparent region, ignore it
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
            # Middle-click: cycle visualization pattern
            next_pattern = self.get_next_pattern()
            self.set_visualization_pattern(next_pattern)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right-click: show context menu (only if in active area)
            if self._is_point_in_active_area(event.position()):
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
        """Handle dismiss action.

        Emits dismissRequested signal which is handled by WindowVisibilityCoordinator
        to switch from persistent to popup mode.
        """
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

        # Apply window properties via KWin every time window is shown
        # This ensures on-all-desktops is correctly set when switching modes
        # Use QTimer to ensure window is fully mapped before applying KWin properties
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._apply_kwin_properties)

    def _apply_kwin_properties(self):
        """Apply window properties via KWin (called after window is shown).

        This method is called every time the window is shown to ensure properties
        are correctly applied, especially when switching between modes.
        """
        from . import kwin_rules

        if not self.windowHandle() or not self.isVisible():
            logger.warning("Cannot apply KWin properties - window not ready")
            return

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
