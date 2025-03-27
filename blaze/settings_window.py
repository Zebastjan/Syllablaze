from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox,
                             QGroupBox, QFormLayout, QProgressBar, QPushButton,
                             QLineEdit, QMessageBox, QApplication, QSystemTrayIcon)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
import logging
import keyboard
from PyQt6.QtGui import QKeySequence
from blaze.settings import Settings
from blaze.constants import APP_NAME, DEFAULT_WHISPER_MODEL
from blaze.whisper_model_manager import WhisperModelTable

logger = logging.getLogger(__name__)

class ShortcutEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click to set shortcut...")
        self.recording = False
        
    def keyPressEvent(self, event):
        if not self.recording:
            return
            
        modifiers = event.modifiers()
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self.recording = False
            return
            
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
            
        # Create key sequence
        sequence = QKeySequence(modifiers | key)
        self.setText(sequence.toString())
        self.recording = False
        self.clearFocus()
        
    def mousePressEvent(self, event):
        self.recording = True
        self.setText("Press shortcut keys...")
        
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.recording = False

class SettingsWindow(QWidget):
    initialization_complete = pyqtSignal()
    shortcuts_changed = pyqtSignal(str, str)  # start_key, stop_key
    
    def showEvent(self, event):
        """Override showEvent to ensure window is properly sized and positioned"""
        super().showEvent(event)
        # Center the window on the screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Settings")
        
        # Initialize settings
        self.settings = Settings()
        
        # Set window to be large
        desktop = QApplication.primaryScreen().availableGeometry()
        self.resize(int(desktop.width() * 0.8), int(desktop.height() * 0.8))
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Model settings group
        model_group = QGroupBox("Whisper Models")
        model_layout = QVBoxLayout()
        
        # Create the model table
        self.model_table = WhisperModelTable()
        self.model_table.model_activated.connect(self.on_model_activated)
        model_layout.addWidget(self.model_table)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Language settings group
        language_group = QGroupBox("Language Settings")
        language_layout = QFormLayout()
        
        self.lang_combo = QComboBox()
        # Add all supported languages
        for code, name in Settings.VALID_LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        current_lang = self.settings.get('language', 'auto')
        # Find and set the current language
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        language_layout.addRow("Language:", self.lang_combo)
        
        language_group.setLayout(language_layout)
        layout.addWidget(language_group)
        
        # Recording settings group
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        self.device_combo = QComboBox()
        self.device_combo.addItems(["Default Microphone"])  # You can populate this with actual devices
        current_mic = self.settings.get('mic_index', 0)
        self.device_combo.setCurrentIndex(current_mic)
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        recording_layout.addRow("Input Device:", self.device_combo)
        
        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)
        
       
        # Add shortcuts group
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QFormLayout()
        
        self.start_shortcut = ShortcutEdit()
        self.start_shortcut.setText(self.settings.get('start_shortcut', 'ctrl+alt+r'))
        self.stop_shortcut = ShortcutEdit()
        self.stop_shortcut.setText(self.settings.get('stop_shortcut', 'ctrl+alt+s'))
        
        shortcuts_layout.addRow("Start Recording:", self.start_shortcut)
        shortcuts_layout.addRow("Stop Recording:", self.stop_shortcut)
        
        apply_btn = QPushButton("Apply Shortcuts")
        apply_btn.clicked.connect(self.apply_shortcuts)
        shortcuts_layout.addRow(apply_btn)
        
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
        # Add stretch to keep widgets at the top
        layout.addStretch()
        
        # Set a reasonable size
        self.setMinimumWidth(300)
        
        # Initialize whisper model
        self.whisper_model = None
        self.current_model = None

    def on_language_changed(self, index):
        import sys
        
        language_code = self.lang_combo.currentData()
        language_name = self.lang_combo.currentText()
        try:
            # Set the language
            self.settings.set('language', language_code)
            
            # Update any active transcriber instances
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'transcriber') and widget.transcriber:
                    widget.transcriber.update_language(language_code)
            
            # Import and use the update_tray_tooltip function
            from blaze.main import update_tray_tooltip
            update_tray_tooltip()
            
            # Log confirmation that the change was successful
            logger.info(f"Language successfully changed to: {language_name} ({language_code})")
            print(f"Language successfully changed to: {language_name} ({language_code})", flush=True)
        except ValueError as e:
            logger.error(f"Failed to set language: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_device_changed(self, index):
        try:
            self.settings.set('mic_index', index)
        except ValueError as e:
            logger.error(f"Failed to set microphone: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_model_activated(self, model_name):
        """Handle model activation from the table"""
        if hasattr(self, 'current_model') and model_name == self.current_model:
            logger.info(f"Model {model_name} is already active, no change needed")
            print(f"Model {model_name} is already active, no change needed")
            return
            
        try:
            # Set the model
            self.settings.set('model', model_name)
            self.current_model = model_name
            
            # No modal dialog needed
            
            # Update any active transcriber instances
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'transcriber') and widget.transcriber:
                    widget.transcriber.update_model(model_name)
            
            # Import and use the update_tray_tooltip function
            from blaze.main import update_tray_tooltip
            update_tray_tooltip()
            
            # Log confirmation that the change was successful
            logger.info(f"Model successfully changed to: {model_name}")
            print(f"Model successfully changed to: {model_name}")
                    
            self.initialization_complete.emit()
        except ValueError as e:
            logger.error(f"Failed to set model: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def apply_shortcuts(self):
        try:
            start_key = self.start_shortcut.text()
            stop_key = self.stop_shortcut.text()
            
            if not start_key or not stop_key:
                QMessageBox.warning(self, "Invalid Shortcuts",
                    "Please set both start and stop shortcuts.")
                return
            
            if start_key == stop_key:
                QMessageBox.warning(self, "Invalid Shortcuts",
                    "Start and stop shortcuts must be different.")
                return
            
            # Save shortcuts to settings
            self.settings.set('start_shortcut', start_key)
            self.settings.set('stop_shortcut', stop_key)
            
            self.shortcuts_changed.emit(start_key, stop_key)
            
        except Exception as e:
            logger.error(f"Error applying shortcuts: {e}")
            QMessageBox.critical(self, "Error",
                "Failed to apply shortcuts. Please try different combinations.")