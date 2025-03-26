from PyQt6.QtCore import QObject, pyqtSignal
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
            
            # Create new shortcuts
            self.start_shortcut = QShortcut(QKeySequence(start_key), QApplication.instance())
            self.start_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self.start_shortcut.activated.connect(self._on_start_triggered)
            
            self.stop_shortcut = QShortcut(QKeySequence(stop_key), QApplication.instance())
            self.stop_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self.stop_shortcut.activated.connect(self._on_stop_triggered)
            
            logger.info(f"Global shortcuts registered - Start: {start_key}, Stop: {stop_key}")
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
        self.remove_shortcuts() 