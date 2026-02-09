from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QFormLayout,
    QPushButton,
    QTabWidget,
    QMessageBox,
    QApplication,
    QCheckBox,
    QSpinBox,
)
from PyQt6.QtCore import QUrl, pyqtSignal, Qt, QProcess
from PyQt6.QtGui import QDesktopServices
import logging
from blaze.settings import Settings
from blaze.constants import (
    APP_NAME,
    APP_VERSION,
    GITHUB_REPO_URL,
    SAMPLE_RATE_MODE_WHISPER,
    SAMPLE_RATE_MODE_DEVICE,
    DEFAULT_SAMPLE_RATE_MODE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_BEAM_SIZE,
    DEFAULT_VAD_FILTER,
    DEFAULT_WORD_TIMESTAMPS,
    DEFAULT_SHORTCUT,
)
from blaze.whisper_model_manager import WhisperModelTableWidget

logger = logging.getLogger(__name__)


class SettingsWindow(QWidget):
    initialization_complete = pyqtSignal()

    def showEvent(self, event):
        """Override showEvent to ensure window is properly sized and positioned"""
        super().showEvent(event)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )
        # Refresh shortcut display from kglobalaccel each time window opens
        if hasattr(self, "shortcut_display"):
            self._refresh_shortcut_display()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Settings")

        self.settings = Settings()
        self.whisper_model = None
        self.current_model = None

        self.setFixedSize(750, 550)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        self.setLayout(layout)

        # Create tab widget with left-side tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)
        layout.addWidget(self.tabs)

        # Build tabs
        self._build_models_tab()
        self._build_audio_tab()
        self._build_transcription_tab()
        self._build_shortcuts_tab()
        self._build_about_tab()

    # ── Tab Builders ──────────────────────────────────────────

    def _build_models_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        self.model_table = WhisperModelTableWidget()
        self.model_table.model_activated.connect(self.on_model_activated)
        tab_layout.addWidget(self.model_table)

        self.tabs.addTab(tab, "Models")

    def _build_audio_tab(self):
        tab = QWidget()
        tab_layout = QFormLayout(tab)

        # Input Device
        self.mic_device_combo = QComboBox()
        self._populate_mic_list()
        self.mic_device_combo.currentIndexChanged.connect(self.on_mic_device_changed)
        tab_layout.addRow("Input Device:", self.mic_device_combo)

        # Refresh button
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self._populate_mic_list)
        tab_layout.addRow("", refresh_btn)

        # Sample Rate Mode
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItem(
            "16kHz - best for Whisper", SAMPLE_RATE_MODE_WHISPER
        )
        self.sample_rate_combo.addItem("Default for device", SAMPLE_RATE_MODE_DEVICE)
        current_mode = self.settings.get("sample_rate_mode", DEFAULT_SAMPLE_RATE_MODE)
        index = self.sample_rate_combo.findData(current_mode)
        if index >= 0:
            self.sample_rate_combo.setCurrentIndex(index)
        self.sample_rate_combo.currentIndexChanged.connect(
            self.on_sample_rate_mode_changed
        )
        tab_layout.addRow("Sample Rate:", self.sample_rate_combo)

        self.tabs.addTab(tab, "Audio")

    def _build_transcription_tab(self):
        tab = QWidget()
        tab_layout = QFormLayout(tab)

        # Language
        self.lang_combo = QComboBox()
        for code, name in Settings.VALID_LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        current_lang = self.settings.get("language", "auto")
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        tab_layout.addRow("Language:", self.lang_combo)

        # Compute Type
        self.compute_type_combo = QComboBox()
        self.compute_type_combo.addItems(["float32", "float16", "int8"])
        self.compute_type_combo.setCurrentText(
            self.settings.get("compute_type", DEFAULT_COMPUTE_TYPE)
        )
        self.compute_type_combo.currentTextChanged.connect(self.on_compute_type_changed)
        tab_layout.addRow("Compute Type:", self.compute_type_combo)

        # Device (cpu/cuda)
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda"])
        self.device_combo.setCurrentText(self.settings.get("device", DEFAULT_DEVICE))
        self.device_combo.currentTextChanged.connect(self.on_device_changed)
        tab_layout.addRow("Device:", self.device_combo)

        # Beam Size
        self.beam_size_spin = QSpinBox()
        self.beam_size_spin.setRange(1, 10)
        self.beam_size_spin.setValue(self.settings.get("beam_size", DEFAULT_BEAM_SIZE))
        self.beam_size_spin.valueChanged.connect(self.on_beam_size_changed)
        tab_layout.addRow("Beam Size:", self.beam_size_spin)

        # VAD Filter
        self.vad_filter_check = QCheckBox("Use Voice Activity Detection (VAD) filter")
        self.vad_filter_check.setChecked(
            self.settings.get("vad_filter", DEFAULT_VAD_FILTER)
        )
        self.vad_filter_check.stateChanged.connect(self.on_vad_filter_changed)
        tab_layout.addRow("", self.vad_filter_check)

        # Word Timestamps
        self.word_timestamps_check = QCheckBox("Generate word timestamps")
        self.word_timestamps_check.setChecked(
            self.settings.get("word_timestamps", DEFAULT_WORD_TIMESTAMPS)
        )
        self.word_timestamps_check.stateChanged.connect(self.on_word_timestamps_changed)
        tab_layout.addRow("", self.word_timestamps_check)

        self.tabs.addTab(tab, "Transcription")

    def _build_shortcuts_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        # Current shortcut display
        form = QFormLayout()
        self.shortcut_display = QLabel(DEFAULT_SHORTCUT)
        self.shortcut_display.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow("Toggle Recording:", self.shortcut_display)
        tab_layout.addLayout(form)

        # Button to open KDE System Settings
        open_btn = QPushButton("Configure in System Settings...")
        open_btn.clicked.connect(self._open_kde_shortcut_settings)
        tab_layout.addWidget(open_btn)

        tab_layout.addSpacing(12)

        # Explanation
        info = QLabel(
            "Shortcuts are managed by KDE System Settings.\n"
            "This provides full Wayland support and native desktop integration.\n"
            "Changes take effect immediately."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        tab_layout.addWidget(info)

        tab_layout.addStretch()
        self.tabs.addTab(tab, "Shortcuts")

    def _build_about_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        name_label = QLabel(f"<h2>{APP_NAME}</h2>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tab_layout.addWidget(name_label)

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tab_layout.addWidget(version_label)

        tab_layout.addStretch()

        github_btn = QPushButton("GitHub Repository")
        github_btn.clicked.connect(self.open_github_repo)
        tab_layout.addWidget(github_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        tab_layout.addStretch()

        self.tabs.addTab(tab, "About")

    # ── Mic Enumeration ───────────────────────────────────────

    def _populate_mic_list(self):
        """Enumerate actual audio input devices via PyAudio.

        Shows only devices with input channels that don't match blocklist patterns.
        Designed for maximum compatibility across different Linux audio setups.
        """
        self.mic_device_combo.blockSignals(True)
        self.mic_device_combo.clear()

        saved_mic_index = self.settings.get("mic_index", None)
        select_combo_index = 0

        # Blocklist of patterns for devices that are NOT microphones
        # This ensures we only show actual microphones and audio inputs
        skip_patterns = [
            # Audio servers and virtual devices
            "pulse",
            "pulseaudio",
            "jack",
            "pipewire",
            "pipe wire",
            # Virtual/loopback devices
            "virtual",
            "loopback",
            "dummy",
            "null",
            # Mixers and routing
            "mix",
            "mixer",
            "up mix",
            "down mix",
            "mix down",
            "remap",
            # Digital audio interfaces (outputs, not inputs)
            "spdif",
            "s/pdif",
            "aes",
            "aes3",
            "s/pdif optical",
            # Browser audio capture
            "browser",
            "firefox",
            "chrome",
            "chromium",
            "fire dragon",
            "web",
            # Virtual audio cables
            "cable",
            "vb-audio",
            "voicemeeter",
            "virtual audio cable",
            # System audio capture (what you hear)
            "system",
            "desktop",
            "stereo mix",
            "what u hear",
            "stereo mix",
            "what u hear",
            "stereo",
            "recording",
            # Generic/unsuitable device names
            "rate",
            "speed",
            "default",
            "null output",
            # Video device audio (HDMI/displayport - usually outputs, not mic inputs)
            "hdmi",
            "displayport",
            "dp audio",
            # Output devices
            "monitor",
            "speaker",
            "headphone",
            "output",
            "digital output",
        ]

        try:
            import pyaudio

            pa = pyaudio.PyAudio()
            try:
                for i in range(pa.get_device_count()):
                    try:
                        info = pa.get_device_info_by_index(i)
                    except Exception:
                        continue

                    # Essential check: must have input channels
                    max_input_channels = info.get("maxInputChannels", 0)
                    if (
                        not isinstance(max_input_channels, int)
                        or max_input_channels <= 0
                    ):
                        continue

                    device_name = str(info.get("name", f"Device {i}")).lower()
                    device_info = f"{info.get('name', f'Device {i}')} (hw:{info.get('hostApi', 0)}, {i})"

                    # Skip if device matches any blocklist pattern
                    skip_device = any(
                        pattern in device_name for pattern in skip_patterns
                    )

                    if skip_device:
                        logger.debug(f"Skipping non-mic device: {device_info}")
                        continue

                    # Device passed all filters - add it
                    name = str(info.get("name", f"Device {i}"))
                    self.mic_device_combo.addItem(name, i)

                    if saved_mic_index is not None and i == saved_mic_index:
                        select_combo_index = self.mic_device_combo.count() - 1

            finally:
                pa.terminate()
        except Exception as e:
            logger.error(f"Failed to enumerate audio devices: {e}")
            # Fallback to default device if enumeration fails
            self.mic_device_combo.addItem("Default Microphone", 0)

        # Handle case where no devices found after filtering
        if self.mic_device_combo.count() == 0:
            self.mic_device_combo.addItem("No microphones found - using default", -1)

        self.mic_device_combo.setCurrentIndex(select_combo_index)
        self.mic_device_combo.blockSignals(False)

        self.mic_device_combo.setCurrentIndex(select_combo_index)
        self.mic_device_combo.blockSignals(False)

    # ── Shortcut Handlers ─────────────────────────────────────

    def _open_kde_shortcut_settings(self):
        """Open KDE System Settings to the Shortcuts page."""
        QProcess.startDetached("systemsettings", ["kcm_keys"])

    def _refresh_shortcut_display(self):
        """Update the shortcut label from kglobalaccel."""
        from blaze.main import tray_recorder_instance

        if tray_recorder_instance and hasattr(tray_recorder_instance, "shortcuts"):
            shortcuts = tray_recorder_instance.shortcuts
            if shortcuts._kglobalaccel_iface:
                import asyncio
                loop = asyncio.get_event_loop()
                loop.create_task(self._async_refresh_shortcut(shortcuts))
                return
            display = shortcuts.current_shortcut_display
            if display:
                self.shortcut_display.setText(display)

    async def _async_refresh_shortcut(self, shortcuts):
        """Query kglobalaccel for the current shortcut and update label."""
        display = await shortcuts.query_current_shortcut()
        if display and hasattr(self, "shortcut_display"):
            self.shortcut_display.setText(display)

    # ── Settings Change Handlers (preserved from original) ────

    def on_language_changed(self, index):
        language_code = self.lang_combo.currentData()
        language_name = self.lang_combo.currentText()
        try:
            self.settings.set("language", language_code)

            from blaze.main import tray_recorder_instance

            if tray_recorder_instance and hasattr(
                tray_recorder_instance, "transcription_manager"
            ):
                tm = tray_recorder_instance.transcription_manager
                if tm:
                    tm.update_language(language_code)

            from blaze.main import update_tray_tooltip

            update_tray_tooltip()

            logger.info(
                f"Language successfully changed to: {language_name} ({language_code})"
            )
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_compute_type_changed(self, value):
        try:
            self.settings.set("compute_type", value)
            logger.info(f"Compute type changed to: {value}")
            QMessageBox.information(
                self,
                "Restart Required",
                "The compute type change will take effect the next time a model is loaded.",
            )
        except ValueError as e:
            logger.error(f"Failed to set compute type: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_device_changed(self, value):
        try:
            self.settings.set("device", value)
            logger.info(f"Device changed to: {value}")
            QMessageBox.information(
                self,
                "Restart Required",
                "The device change will take effect the next time a model is loaded.",
            )
        except ValueError as e:
            logger.error(f"Failed to set device: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_beam_size_changed(self, value):
        try:
            self.settings.set("beam_size", value)
            logger.info(f"Beam size changed to: {value}")
        except ValueError as e:
            logger.error(f"Failed to set beam size: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_vad_filter_changed(self, state):
        try:
            value = state == Qt.CheckState.Checked
            self.settings.set("vad_filter", value)
            logger.info(f"VAD filter changed to: {value}")
        except ValueError as e:
            logger.error(f"Failed to set VAD filter: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_word_timestamps_changed(self, state):
        try:
            value = state == Qt.CheckState.Checked
            self.settings.set("word_timestamps", value)
            logger.info(f"Word timestamps changed to: {value}")
        except ValueError as e:
            logger.error(f"Failed to set word timestamps: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_mic_device_changed(self, index):
        if index < 0:
            return
        device_index = self.mic_device_combo.currentData()
        if device_index is None or device_index < 0:
            return
        try:
            self.settings.set("mic_index", device_index)
            logger.info(f"Microphone changed to device index: {device_index}")
        except ValueError as e:
            logger.error(f"Failed to set microphone: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_sample_rate_mode_changed(self, index):
        try:
            mode = self.sample_rate_combo.currentData()
            self.settings.set("sample_rate_mode", mode)

            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if hasattr(widget, "recorder") and widget.recorder:
                    if hasattr(widget.recorder, "update_sample_rate_mode"):
                        widget.recorder.update_sample_rate_mode(mode)

            logger.info(f"Sample rate mode changed to: {mode}")
        except ValueError as e:
            logger.error(f"Failed to set sample rate mode: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_model_activated(self, model_name):
        """Handle model activation from the table"""
        if hasattr(self, "current_model") and model_name == self.current_model:
            logger.info(f"Model {model_name} is already active, no change needed")
            return

        try:
            self.settings.set("model", model_name)
            self.current_model = model_name

            from blaze.main import tray_recorder_instance

            if tray_recorder_instance and hasattr(
                tray_recorder_instance, "transcription_manager"
            ):
                tm = tray_recorder_instance.transcription_manager
                if tm:
                    tm.update_model(model_name)

            from blaze.main import update_tray_tooltip

            update_tray_tooltip()

            logger.info(f"Model successfully changed to: {model_name}")
            self.initialization_complete.emit()
        except Exception as e:
            logger.error(f"Failed to set model: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def open_github_repo(self):
        """Open the GitHub repository in the default browser"""
        QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))
