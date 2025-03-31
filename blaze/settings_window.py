from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox,
                             QGroupBox, QFormLayout, QPushButton,
                             QMessageBox, QApplication, QCheckBox, QSpinBox,
                             QHBoxLayout, QSizePolicy)
from PyQt6.QtCore import QUrl, pyqtSignal, Qt
from PyQt6.QtGui import QDesktopServices
import logging
from blaze.settings import Settings
from blaze.constants import (
    APP_NAME, APP_VERSION, GITHUB_REPO_URL,
    SAMPLE_RATE_MODE_WHISPER, SAMPLE_RATE_MODE_DEVICE, DEFAULT_SAMPLE_RATE_MODE,
    DEFAULT_COMPUTE_TYPE, DEFAULT_DEVICE, DEFAULT_BEAM_SIZE, DEFAULT_VAD_FILTER, DEFAULT_WORD_TIMESTAMPS
)
from blaze.whisper_model_manager import WhisperModelTableWidget

logger = logging.getLogger(__name__)

class SettingsWindow(QWidget):
    initialization_complete = pyqtSignal()
    
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
        
        # Set window to maximize height while keeping width reasonable
        desktop = QApplication.primaryScreen().availableGeometry()
        self.resize(int(desktop.width() * 0.6), int(desktop.height() * 0.9))
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Model settings group - make it expand to fill available space
        model_group = QGroupBox("Faster Whisper Models")
        model_layout = QVBoxLayout()
        
        # Create the model table
        self.model_table = WhisperModelTableWidget()
        self.model_table.model_activated.connect(self.on_model_activated)
        model_layout.addWidget(self.model_table)
        
        model_group.setLayout(model_layout)
        # Set size policy to make this group expand vertically
        model_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(model_group)
        
        # Language settings group
        language_group = QGroupBox("Language Settings")
        language_layout = QFormLayout()
        
        self.lang_combo = QComboBox()
        # Set a reasonable width for the combo box
        self.lang_combo.setMaximumWidth(300)
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
        # Set size policy to make this group not expand
        language_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout.addWidget(language_group)
        
        # Faster Whisper settings group
        faster_whisper_group = QGroupBox("Faster Whisper Settings")
        faster_whisper_layout = QFormLayout()
        
        # Compute type selection
        self.compute_type_combo = QComboBox()
        self.compute_type_combo.setMaximumWidth(300)
        self.compute_type_combo.addItems(['float32', 'float16', 'int8'])
        self.compute_type_combo.setCurrentText(self.settings.get('compute_type', DEFAULT_COMPUTE_TYPE))
        self.compute_type_combo.currentTextChanged.connect(self.on_compute_type_changed)
        faster_whisper_layout.addRow("Compute Type:", self.compute_type_combo)
        
        # Device selection
        self.device_combo = QComboBox()
        self.device_combo.setMaximumWidth(300)
        self.device_combo.addItems(['cpu', 'cuda'])
        self.device_combo.setCurrentText(self.settings.get('device', DEFAULT_DEVICE))
        self.device_combo.currentTextChanged.connect(self.on_device_changed)
        faster_whisper_layout.addRow("Device:", self.device_combo)
        
        # Beam size
        self.beam_size_spin = QSpinBox()
        self.beam_size_spin.setMaximumWidth(300)
        self.beam_size_spin.setRange(1, 10)
        self.beam_size_spin.setValue(self.settings.get('beam_size', DEFAULT_BEAM_SIZE))
        self.beam_size_spin.valueChanged.connect(self.on_beam_size_changed)
        faster_whisper_layout.addRow("Beam Size:", self.beam_size_spin)
        
        # VAD filter
        self.vad_filter_check = QCheckBox("Use Voice Activity Detection (VAD) filter")
        self.vad_filter_check.setChecked(self.settings.get('vad_filter', DEFAULT_VAD_FILTER))
        self.vad_filter_check.stateChanged.connect(self.on_vad_filter_changed)
        faster_whisper_layout.addRow("", self.vad_filter_check)
        
        # Word timestamps
        self.word_timestamps_check = QCheckBox("Generate word timestamps")
        self.word_timestamps_check.setChecked(self.settings.get('word_timestamps', DEFAULT_WORD_TIMESTAMPS))
        self.word_timestamps_check.stateChanged.connect(self.on_word_timestamps_changed)
        faster_whisper_layout.addRow("", self.word_timestamps_check)
        
        faster_whisper_group.setLayout(faster_whisper_layout)
        # Set size policy to make this group not expand
        faster_whisper_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout.addWidget(faster_whisper_group)
        
        # Recording settings group
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        self.mic_device_combo = QComboBox()
        # Set a reasonable width for the combo box
        self.mic_device_combo.setMaximumWidth(300)
        self.mic_device_combo.addItems(["Default Microphone"])  # You can populate this with actual devices
        current_mic = self.settings.get('mic_index', 0)
        self.mic_device_combo.setCurrentIndex(current_mic)
        self.mic_device_combo.currentIndexChanged.connect(self.on_mic_device_changed)
        recording_layout.addRow("Input Device:", self.mic_device_combo)
        
        # Add sample rate mode option
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.setMaximumWidth(300)
        self.sample_rate_combo.addItem("16kHz - best for Whisper", SAMPLE_RATE_MODE_WHISPER)
        self.sample_rate_combo.addItem("Default for device", SAMPLE_RATE_MODE_DEVICE)
        current_mode = self.settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
        index = self.sample_rate_combo.findData(current_mode)
        if index >= 0:
            self.sample_rate_combo.setCurrentIndex(index)
        self.sample_rate_combo.currentIndexChanged.connect(self.on_sample_rate_mode_changed)
        recording_layout.addRow("Sample Rate:", self.sample_rate_combo)
        
        recording_group.setLayout(recording_layout)
        # Set size policy to make this group not expand
        recording_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout.addWidget(recording_group)
        
        # No stretch here to allow the table to expand and fill available space
        
        # Add version and GitHub repo link at the bottom
        footer_layout = QHBoxLayout()
        
        # Version label
        version_label = QLabel(f"Version: {APP_VERSION}")
        footer_layout.addWidget(version_label)
        
        # Spacer to push items to the edges
        footer_layout.addStretch()
        
        # GitHub repo link
        github_link = QPushButton("GitHub Repository")
        github_link.clicked.connect(self.open_github_repo)
        footer_layout.addWidget(github_link)
        
        layout.addLayout(footer_layout)
        
        # Set a reasonable size
        self.setMinimumWidth(500)
        
        # Initialize whisper model
        self.whisper_model = None
        self.current_model = None

    def on_language_changed(self, index):
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

    def on_compute_type_changed(self, value):
        try:
            self.settings.set('compute_type', value)
            logger.info(f"Compute type changed to: {value}")
            print(f"Compute type changed to: {value}")
            QMessageBox.information(self, "Restart Required",
                                   "The compute type change will take effect the next time a model is loaded.")
        except ValueError as e:
            logger.error(f"Failed to set compute type: {e}")
            QMessageBox.warning(self, "Error", str(e))
            
    def on_device_changed(self, value):
        try:
            self.settings.set('device', value)
            logger.info(f"Device changed to: {value}")
            print(f"Device changed to: {value}")
            QMessageBox.information(self, "Restart Required",
                                   "The device change will take effect the next time a model is loaded.")
        except ValueError as e:
            logger.error(f"Failed to set device: {e}")
            QMessageBox.warning(self, "Error", str(e))
            
    def on_beam_size_changed(self, value):
        try:
            self.settings.set('beam_size', value)
            logger.info(f"Beam size changed to: {value}")
            print(f"Beam size changed to: {value}")
        except ValueError as e:
            logger.error(f"Failed to set beam size: {e}")
            QMessageBox.warning(self, "Error", str(e))
            
    def on_vad_filter_changed(self, state):
        try:
            value = state == Qt.CheckState.Checked
            self.settings.set('vad_filter', value)
            logger.info(f"VAD filter changed to: {value}")
            print(f"VAD filter changed to: {value}")
        except ValueError as e:
            logger.error(f"Failed to set VAD filter: {e}")
            QMessageBox.warning(self, "Error", str(e))
            
    def on_word_timestamps_changed(self, state):
        try:
            value = state == Qt.CheckState.Checked
            self.settings.set('word_timestamps', value)
            logger.info(f"Word timestamps changed to: {value}")
            print(f"Word timestamps changed to: {value}")
        except ValueError as e:
            logger.error(f"Failed to set word timestamps: {e}")
            QMessageBox.warning(self, "Error", str(e))
            
    def on_mic_device_changed(self, index):
        try:
            self.settings.set('mic_index', index)
        except ValueError as e:
            logger.error(f"Failed to set microphone: {e}")
            QMessageBox.warning(self, "Error", str(e))
            
    def on_sample_rate_mode_changed(self, index):
        try:
            mode = self.sample_rate_combo.currentData()
            self.settings.set('sample_rate_mode', mode)
            
            # Update any active recorder instances
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'recorder') and widget.recorder:
                    # Signal the recorder to update its sample rate mode
                    # This will apply on the next recording
                    if hasattr(widget.recorder, 'update_sample_rate_mode'):
                        widget.recorder.update_sample_rate_mode(mode)
            
            logger.info(f"Sample rate mode changed to: {mode}")
        except ValueError as e:
            logger.error(f"Failed to set sample rate mode: {e}")
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

    def open_github_repo(self):
        """Open the GitHub repository in the default browser"""
        QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))