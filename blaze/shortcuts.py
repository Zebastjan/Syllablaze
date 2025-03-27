from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication
import logging

logger = logging.getLogger(__name__)

class GlobalShortcuts(QObject):
    start_recording_triggered = pyqtSignal()
    stop_recording_triggered = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.start_shortcut = None
        self.stop_shortcut = None
        
    def setup_shortcuts(self, start_key='Ctrl+Alt+R', stop_key='Ctrl+Alt+S'):
        """Setup global keyboard shortcuts"""
        try:
            # Remove any existing shortcuts
            self.remove_shortcuts()
            
            # Create new shortcuts if keys are provided
            if start_key:
                self.start_shortcut = QShortcut(QKeySequence(start_key), QApplication.instance())
                self.start_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
                self.start_shortcut.activated.connect(self._on_start_triggered)
            
            if stop_key:
                self.stop_shortcut = QShortcut(QKeySequence(stop_key), QApplication.instance())
                self.stop_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
                self.stop_shortcut.activated.connect(self._on_stop_triggered)
            
            # Format log message to show "not set" for empty shortcuts
            start_display = start_key if start_key else "not set"
            stop_display = stop_key if stop_key else "not set"
            logger.info(f"Global shortcuts registered - Start: {start_display}, Stop: {stop_display}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register global shortcuts: {e}")
            return False
    
    def remove_shortcuts(self):
        """Remove existing shortcuts"""
        if self.start_shortcut:
            self.start_shortcut.setEnabled(False)
            self.start_shortcut.deleteLater()
            self.start_shortcut = None
            
        if self.stop_shortcut:
            self.stop_shortcut.setEnabled(False)
            self.stop_shortcut.deleteLater()
            self.stop_shortcut = None
    
    def _on_start_triggered(self):
        """Called when start recording shortcut is pressed"""
        logger.info("Start recording shortcut triggered")
        self.start_recording_triggered.emit()
        
    def _on_stop_triggered(self):
        """Called when stop recording shortcut is pressed"""
        logger.info("Stop recording shortcut triggered")
        self.stop_recording_triggered.emit()
        
    def __del__(self):
        try:
            if hasattr(self, 'start_shortcut') and self.start_shortcut is not None:
                self.remove_shortcuts()
        except RuntimeError:
            # Handle case where Qt objects have already been deleted
            logger.debug("Qt objects already deleted during cleanup")