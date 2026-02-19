import os
import sys

# Set QML import path for Kirigami before importing any Qt modules
os.environ["QML2_IMPORT_PATH"] = "/usr/lib/qt6/qml"

from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon, QAction
import logging
from blaze.kirigami_integration import KirigamiSettingsWindow as SettingsWindow
from blaze.progress_window import ProgressWindow
from blaze.loading_window import LoadingWindow
from blaze.recording_dialog_manager import RecordingDialogManager
from PyQt6.QtCore import pyqtSignal
from blaze.settings import Settings
from blaze.shortcuts import GlobalShortcuts
from blaze.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_SHORTCUT,
    ORG_NAME,
    VALID_LANGUAGES,
    LOCK_FILE_PATH,
)
from blaze.managers.ui_manager import UIManager
from blaze.managers.lock_manager import LockManager
from blaze.managers.audio_manager import AudioManager
from blaze.managers.transcription_manager import TranscriptionManager
from blaze.managers.tray_menu_manager import TrayMenuManager
from blaze.managers.settings_coordinator import SettingsCoordinator
from blaze.managers.window_visibility_coordinator import WindowVisibilityCoordinator
from blaze.managers.gpu_setup_manager import GPUSetupManager
from blaze.clipboard_manager import ClipboardManager
from blaze.application_state import ApplicationState
from blaze.services.notification_service import NotificationService
from blaze.services.clipboard_persistence_service import ClipboardPersistenceService
from blaze import orchestration

import asyncio
from dbus_next.service import ServiceInterface, method
from dbus_next.aio import MessageBus
import qasync

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio error handling is now done in recorder.py
# This comment is kept for documentation purposes

# Global reference to the tray icon instance, used by update_tray_tooltip()
tray_recorder_instance = None


def update_tray_tooltip():
    """Update the tray tooltip with current model info"""
    if tray_recorder_instance:
        tray_recorder_instance.update_tooltip()


class SyllaDBusService(ServiceInterface):
    def __init__(self, tray_app):
        super().__init__("org.kde.Syllablaze")
        self.tray_app = tray_app

    @method()
    def ToggleRecording(self) -> None:
        """Toggle recording via D-Bus"""
        logger.info("D-Bus ToggleRecording method called")
        self.tray_app.toggle_recording()


def check_dependencies():
    required_packages = ["faster_whisper", "pyaudio", "keyboard"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
            logger.error(f"Failed to import required dependency: {package}")

    if missing_packages:
        error_msg = (
            "Missing required dependencies:\n"
            f"{', '.join(missing_packages)}\n\n"
            "Please install them using:\n"
            f"pip install {' '.join(missing_packages)}"
        )
        QMessageBox.critical(None, "Missing Dependencies", error_msg)
        return False

    return True


class SyllablazeOrchestrator(QSystemTrayIcon):
    initialization_complete = pyqtSignal()

    def __init__(self, settings=None, app_state=None):
        super().__init__()

        # Store settings and app state
        self.settings = settings if settings is not None else Settings()
        self.app_state = app_state

        # Shutdown state
        self._is_shutting_down = False
        self._dbus_bus = None

        # Window references
        self.settings_window = None
        self.processing_window = None
        self.recording_dialog = None

        # Initialize managers
        self.ui_manager = UIManager()
        self.tray_menu_manager = TrayMenuManager()
        self.audio_manager = None
        self.transcription_manager = None
        self.clipboard_manager = None  # Will be initialized in initialize()

        # Add shortcuts handler
        self.shortcuts = GlobalShortcuts()
        self.shortcuts.toggle_recording_triggered.connect(self.toggle_recording)

        # Set tooltip
        self.setToolTip(f"{APP_NAME} {APP_VERSION}")

        # Enable activation by left click
        self.activated.connect(self.on_activate)

    def initialize(self):
        """Initialize the tray recorder after showing loading window"""
        logger.info("SyllablazeOrchestrator: Initializing...")
        # Set application icon
        self.app_icon = QIcon.fromTheme("syllablaze")
        if self.app_icon.isNull():
            # Try to load from local path (resources directory)
            local_icon_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "resources",
                "syllablaze.svg",
            )
            if os.path.exists(local_icon_path):
                self.app_icon = QIcon(local_icon_path)
            else:
                # Fallback to theme icons if custom icon not found
                self.app_icon = QIcon.fromTheme("media-record")
                logger.warning(
                    "Could not load syllablaze icon, using system theme icon"
                )

        # Set the icon for both app and tray
        QApplication.instance().setWindowIcon(self.app_icon)
        self.setIcon(self.app_icon)

        # Phase 6: Initialize icons in UIManager
        self.ui_manager.initialize_icons(self.app_icon)

        # Create menu
        self.setup_menu()

        # Initialize notification service (decoupled from clipboard)
        logger.info("Initializing notification service...")
        self.notification_service = NotificationService(self.settings)
        logger.info("Notification service initialized")

        # Initialize clipboard persistence service (long-running for Wayland)
        logger.info("Initializing clipboard persistence service...")
        self.clipboard_persistence_service = ClipboardPersistenceService(self.settings)
        logger.info("Clipboard persistence service initialized")

        # Initialize clipboard manager (pure service, no UI deps)
        logger.info("Initializing clipboard manager...")
        self.clipboard_manager = ClipboardManager(
            self.settings, self.clipboard_persistence_service
        )
        logger.info("Clipboard manager initialized")

        # Connect clipboard signals to notification service
        self.clipboard_manager.transcription_copied.connect(
            self.notification_service.notify_transcription_complete
        )
        self.clipboard_manager.clipboard_error.connect(
            lambda err: self.notification_service.notify_error("Clipboard Error", err)
        )

        # Connect notification service signals to UI
        self.notification_service.notification_requested.connect(
            lambda title, msg, icon: self.ui_manager.show_notification(
                self, title, msg, self.ui_manager.normal_icon
            )
        )
        self.notification_service.transcription_complete.connect(
            lambda text: self.ui_manager.show_notification(
                self, "Transcription Complete", text, self.ui_manager.normal_icon
            )
        )
        self.notification_service.error_occurred.connect(
            lambda title, msg: self.ui_manager.show_notification(
                self, title, msg, self.ui_manager.normal_icon
            )
        )

        # Initialize settings window early to connect signals
        logger.info("Initializing settings window for signal connections...")
        self.settings_window = SettingsWindow(self.settings)
        logger.info("Settings window created")

        # Initialize recording dialog
        try:
            logger.info("Initializing recording dialog...")
            self.recording_dialog = RecordingDialogManager(
                self.settings, self.app_state
            )
            self.recording_dialog.initialize()

            # Note: Bridge signal connections happen later in _connect_signals()
            # after set_audio_manager() creates the applet and bridge

            # Initialize settings coordinator after recording dialog
            self.settings_coordinator = SettingsCoordinator(
                recording_dialog=self.recording_dialog,
                app_state=self.app_state,
                settings=self.settings,
                tray_menu_manager=self.tray_menu_manager,
            )

            # Connect settings window to coordinator
            self.settings_window.settings_bridge.settingChanged.connect(
                self.settings_coordinator.on_setting_changed
            )
            logger.info("Settings coordinator initialized and signals connected")

            # Initialize window visibility coordinator
            self.window_visibility_coordinator = WindowVisibilityCoordinator(
                recording_dialog=self.recording_dialog,
                app_state=self.app_state,
                tray_menu_manager=self.tray_menu_manager,
                settings_bridge=self.settings_window.settings_bridge,
                settings=self.settings,
                settings_coordinator=self.settings_coordinator,
            )

            # Connect to ApplicationState visibility changes
            if self.app_state:
                self.app_state.recording_dialog_visibility_changed.connect(
                    self.window_visibility_coordinator.on_dialog_visibility_changed
                )

            # Note: Dialog dismissal signal connected later in _connect_signals()
            # after the bridge is created
            logger.info(
                "Window visibility coordinator initialized and signals connected"
            )

            # Set initial dialog visibility (through ApplicationState)
            # This will trigger _on_dialog_visibility_changed which shows/hides the window
            initial_visibility = self.settings.get("show_recording_dialog", True)
            if self.app_state:
                self.app_state.set_recording_dialog_visible(
                    initial_visibility, source="startup"
                )
            logger.info("Recording dialog initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize recording dialog: {e}", exc_info=True)
            self.recording_dialog = None

        # Setup global shortcuts with saved preference
        # Note: Shortcuts are set up after D-Bus is connected in the main async flow

        # Initialize tooltip with model information
        self.update_tooltip()

    def setup_menu(self):
        menu = self.tray_menu_manager.create_menu(
            toggle_recording_callback=self.toggle_recording,
            toggle_settings_callback=self.toggle_settings,
            toggle_dialog_callback=self._toggle_recording_dialog,
            quit_callback=self.quit_application,
        )
        self.setContextMenu(menu)

        # Set initial tray menu text based on current applet_autohide setting
        autohide = bool(self.settings.get("applet_autohide", True))
        self.tray_menu_manager.update_dialog_action(autohide)

    @staticmethod
    def isSystemTrayAvailable():
        return QSystemTrayIcon.isSystemTrayAvailable()

    def toggle_recording(self):
        """Toggle recording state"""
        if self._is_shutting_down:
            logger.info("Ignoring toggle_recording during shutdown")
            return
        # Acquire lock to prevent concurrent operations
        if not self.audio_manager.acquire_recording_lock():
            logger.info("Recording toggle already in progress, ignoring request")
            return

        try:
            # Check readiness if starting recording
            if not self.app_state.is_recording():
                ready, error_msg = self.audio_manager.is_ready_to_record(
                    self.transcription_manager, self.app_state
                )
                if not ready:
                    self.ui_manager.show_notification(
                        self,
                        "Cannot Record",
                        error_msg,
                        self.ui_manager.normal_icon,
                    )
                    # If no model, open settings
                    if "model" in error_msg.lower():
                        self.toggle_settings()
                    return

            # Log state transition
            is_recording = self.app_state.is_recording()
            current_state = "recording" if is_recording else "not recording"
            new_state = "stop recording" if is_recording else "start recording"
            logger.info(f"Toggle recording: {current_state} -> {new_state}")

            # Execute stop or start flow
            if self.app_state.is_recording():
                self._execute_recording_stop()
            else:
                self._execute_recording_start()
        finally:
            # Always release the lock
            self.audio_manager.release_recording_lock()

    def _update_recording_ui(self, recording):
        """Update UI elements for recording state changes"""
        self.tray_menu_manager.update_recording_action(recording)
        self.ui_manager.update_tray_icon_state(recording, self)

    def _revert_recording_ui_on_error(self, was_recording, close_window=False):
        """Revert UI state when recording operation fails"""
        self._update_recording_ui(was_recording)
        if close_window:
            self.ui_manager.close_progress_window("after error")

    def _setup_progress_window_for_recording(self):
        """Create and configure progress window for recording session"""
        progress_window = self.ui_manager.create_progress_window(
            self.settings, "Voice Recording"
        )
        if progress_window:
            # Set reference for settings coordinator
            self.settings_coordinator.set_progress_window(progress_window)
            progress_window.stop_clicked.connect(self._stop_recording)
            # Make sure window is visible and on top
            progress_window.show()
            progress_window.raise_()
            progress_window.activateWindow()
            logger.info("Progress window shown")
        return progress_window

    def _handle_recording_start_failure(self, error=None):
        """Handle errors when starting recording fails"""
        if error:
            logger.error(f"Error starting recording: {error}")
        else:
            logger.error("Failed to start recording")
        self._revert_recording_ui_on_error(was_recording=False, close_window=True)

    def _handle_recording_stop_failure(self, error=None):
        """Handle errors when stopping recording fails"""
        if error:
            logger.error(f"Error stopping recording: {error}")
        else:
            logger.error("Failed to stop recording")
        self._revert_recording_ui_on_error(was_recording=True, close_window=True)

    def _execute_recording_stop(self):
        """Execute the stop recording flow with proper state transitions"""
        # Update UI first to give immediate feedback
        self._update_recording_ui(False)

        # Mark as transcribing via app_state
        self.app_state.start_transcription()

        # Update progress window before stopping recording
        progress_window = self.ui_manager.get_progress_window()
        if progress_window:
            progress_window.set_processing_mode()
            progress_window.set_status("Processing audio...")

        # Stop the actual recording
        if self.audio_manager:
            try:
                # Only change recording state after successful stop
                result = self.audio_manager.stop_recording()
                if result:
                    self.app_state.stop_recording()
                    logger.info("Recording stopped successfully")
                else:
                    # Revert UI if stop failed
                    self._handle_recording_stop_failure()
            except Exception as e:
                # Revert UI if exception occurred
                self._handle_recording_stop_failure(error=e)
        else:
            # No audio manager, just update state
            self.app_state.stop_recording()

    def _execute_recording_start(self):
        """Execute the start recording flow with proper state transitions"""
        # Create and setup progress window
        self._setup_progress_window_for_recording()

        # Update UI to give immediate feedback
        self._update_recording_ui(True)

        # Start the actual recording
        if self.audio_manager:
            try:
                # Only change recording state after successful start
                result = self.audio_manager.start_recording()
                if result:
                    self.app_state.start_recording()
                    logger.info("Recording started successfully")
                else:
                    # Revert UI if start failed
                    self._handle_recording_start_failure()
            except Exception as e:
                # Revert UI if exception occurred
                self._handle_recording_start_failure(error=e)
        else:
            # No audio manager, just update state
            self.app_state.start_recording()

    def _stop_recording(self):
        """Internal method to stop recording and start processing"""
        if not self.recording:
            return

        logger.info("SyllablazeOrchestrator: Stopping recording")
        self.toggle_recording()  # This is now safe since toggle_recording handles everything

    def toggle_settings(self):
        logger.info("====== toggle_settings() called ======")

        # Settings window is now created early in initialize(), so just use it
        if not self.settings_window:
            logger.warning("Settings window not initialized - creating now")
            self.settings_window = SettingsWindow(self.settings)
            # Note: Signal connection to settings coordinator happens in initialize()

        current_visibility = self.settings_window.isVisible()
        logger.info(f"Current settings window visibility: {current_visibility}")

        if current_visibility:
            logger.info("Hiding settings window")
            self.settings_window.hide()
        else:
            logger.info("Showing settings window")
            self.settings_window.show()

            # Wayland-proper window activation
            # On Wayland, QWindow.requestActivate() is the correct method
            # On X11, raise_() + activateWindow() work as fallback
            if self.settings_window.windowHandle():
                logger.info("Using QWindow.requestActivate() for Wayland")
                self.settings_window.windowHandle().requestActivate()
            else:
                # Fallback for X11 or if window handle not ready
                logger.info("Using raise_() + activateWindow() for X11 fallback")
                self.settings_window.raise_()
                self.settings_window.activateWindow()

            logger.info("Settings window shown and activated")

    def _toggle_recording_dialog(self):
        """Toggle recording dialog visibility via tray menu"""
        self.window_visibility_coordinator.toggle_visibility(source="tray_menu")

    def update_tooltip(self, recognized_text=None):
        """Update the tooltip with app name, version, model and language information"""
        import sys

        # Phase 6: Use UIManager to generate tooltip text
        tooltip = self.ui_manager.get_tooltip_text(
            self.settings, recognized_text=recognized_text
        )

        # Print tooltip info to console with flush
        model_name = self.settings.get("model", DEFAULT_WHISPER_MODEL)
        language_code = self.settings.get("language", "auto")
        if language_code in VALID_LANGUAGES:
            language_display = f"Language: {VALID_LANGUAGES[language_code]}"
        else:
            language_display = (
                "Language: auto-detect"
                if language_code == "auto"
                else f"Language: {language_code}"
            )
        print(f"TOOLTIP UPDATE: MODEL={model_name}, {language_display}", flush=True)
        sys.stdout.flush()

        self.setToolTip(tooltip)

    # Removed update_shortcuts method as part of keyboard shortcut functionality removal

    def on_activate(self, reason):
        """Handle tray icon activation with improved resilience"""
        # Ignore activations if we're already processing a click
        if hasattr(self, "_activation_lock") and self._activation_lock:
            logger.info("Activation already in progress, ignoring request")
            return

        # Set lock
        self._activation_lock = True

        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
                logger.info("Tray icon left-clicked")

                # Phase 6: Check if we're in the middle of processing a recording
                progress_window = self.ui_manager.get_progress_window()
                if progress_window and progress_window.isVisible():
                    if not self.recording and getattr(
                        progress_window, "processing", False
                    ):
                        logger.info("Processing in progress, ignoring activation")
                        return

                # Check if transcriber is properly initialized
                if (
                    hasattr(self, "transcription_manager")
                    and self.transcription_manager
                    and hasattr(self.transcription_manager.transcriber, "model")
                    and self.transcription_manager.transcriber.model
                ):
                    # Transcriber is properly initialized, proceed with recording
                    self.toggle_recording()
                else:
                    # Transcriber is not properly initialized, show a message
                    self.ui_manager.show_notification(
                        self,
                        "No Models Downloaded",
                        "No Whisper models are downloaded. Please go to Settings to download a model.",
                        self.ui_manager.normal_icon,
                    )
                    # Open settings window to allow user to download a model
                    self.toggle_settings()
        finally:
            # Always release the lock
            self._activation_lock = False

    def quit_application(self):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        try:
            # 1. Stop recording first (before touching audio hardware)
            self._stop_active_recording()
            # 2. Wait for transcription thread (with force-terminate fallback)
            self._wait_for_threads()
            # 3. Close all UI windows (including recording dialog)
            self._close_windows()
            # 4. Cleanup clipboard persistence service
            self._cleanup_clipboard_service()
            # 5. Release audio hardware last
            self._cleanup_recorder()

            logger.info("Application shutdown complete, exiting...")

            # Explicitly quit the application
            QApplication.instance().quit()

        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            # Force exit if there was an error
            sys.exit(1)

    def _cleanup_recorder(self):
        if self.audio_manager:
            try:
                self.audio_manager.cleanup()
            except Exception as rec_error:
                logger.error(f"Error cleaning up recorder: {rec_error}")
            self.audio_manager = None

    def _cleanup_clipboard_service(self):
        """Cleanup clipboard persistence service."""
        if (
            hasattr(self, "clipboard_persistence_service")
            and self.clipboard_persistence_service
        ):
            try:
                logger.info("Shutting down clipboard persistence service...")
                self.clipboard_persistence_service.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down clipboard persistence service: {e}")
            self.clipboard_persistence_service = None

        if hasattr(self, "clipboard_manager") and self.clipboard_manager:
            try:
                logger.info("Shutting down clipboard manager...")
                self.clipboard_manager.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down clipboard manager: {e}")
            self.clipboard_manager = None

    def _close_windows(self):
        # Close recording dialog (QML engine + window)
        if self.recording_dialog:
            try:
                self.recording_dialog.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up recording dialog: {e}")

        # Close settings window
        if hasattr(self, "settings_window") and self.settings_window:
            self.ui_manager.safely_close_window(self.settings_window, "settings")

        # Close progress window via UIManager
        self.ui_manager.close_progress_window("shutdown")

    def _stop_active_recording(self):
        if self.app_state and self.app_state.is_recording():
            try:
                self._stop_recording()
            except Exception as rec_error:
                logger.error(f"Error stopping recording: {rec_error}")

    def _wait_for_threads(self):
        if hasattr(self, "transcription_manager") and self.transcription_manager:
            try:
                self.transcription_manager.cleanup()
            except Exception as thread_error:
                logger.error(f"Error waiting for transcription worker: {thread_error}")

    async def _cleanup_dbus(self):
        """Disconnect the D-Bus bus if we hold one"""
        if self._dbus_bus:
            try:
                self._dbus_bus.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting D-Bus: {e}")
            self._dbus_bus = None

    def _update_volume_display(self, volume_level):
        """Update the UI with current volume level"""
        # Phase 6: Get progress window from UIManager, check recording from app_state
        progress_window = self.ui_manager.get_progress_window()
        if progress_window and self.app_state and self.app_state.is_recording():
            progress_window.update_volume(volume_level)

    def _handle_recording_completed(self, normalized_audio_data):
        """Handle completion of audio recording and start transcription

        Parameters:
        -----------
        normalized_audio_data : np.ndarray
            Audio data normalized to range [-1.0, 1.0] and ready for transcription

        Notes:
        ------
        - Updates UI to processing mode
        - Starts transcription process
        - Handles any errors during transcription setup
        """
        logger.info(
            "SyllablazeOrchestrator: Recording processed, starting transcription"
        )

        # Phase 5: update_transcribing_state() call removed - AudioBridge listens to app_state

        # Ensure progress window is in processing mode (if enabled)
        # Phase 6: Get progress window from UIManager
        progress_window = self.ui_manager.get_progress_window()
        if progress_window:
            progress_window.set_processing_mode()
            progress_window.set_status("Starting transcription...")
        else:
            logger.debug(
                "Progress window not shown (disabled in settings or not available)"
            )

        try:
            if not self.transcription_manager:
                raise RuntimeError("Transcriber not initialized")
            logger.info(f"Transcriber ready: {self.transcription_manager}")

            if (
                not hasattr(self.transcription_manager.transcriber, "model")
                or not self.transcription_manager.transcriber.model
            ):
                raise RuntimeError("Whisper model not loaded")

            self.transcription_manager.transcribe_audio(normalized_audio_data)

        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            # Phase 6: Use UIManager to close progress window
            self.ui_manager.close_progress_window("after transcription error")

            self.ui_manager.show_notification(
                self,
                "Error",
                f"Failed to start transcription: {str(e)}",
                self.ui_manager.normal_icon,
            )

    def handle_recording_error(self, error):
        """Handle recording errors"""
        logger.error(f"SyllablazeOrchestrator: Recording error: {error}")

        # Show notification instead of dialog
        self.ui_manager.show_notification(
            self, "Recording Error", error, self.ui_manager.normal_icon
        )

        self._stop_recording()
        # Phase 6: Use UIManager to close progress window
        self.ui_manager.close_progress_window("after recording error")

    def update_processing_status(self, status):
        # Phase 6: Get progress window from UIManager
        progress_window = self.ui_manager.get_progress_window()
        if progress_window:
            progress_window.set_status(status)

    def update_processing_progress(self, percent):
        # Phase 6: Get progress window from UIManager
        progress_window = self.ui_manager.get_progress_window()
        if progress_window:
            progress_window.update_progress(percent)

    def _close_progress_window(self, context=""):
        """Helper method to safely close progress window (delegates to UIManager)"""
        # Phase 6: Delegate to UIManager
        self.ui_manager.close_progress_window(context)

    def handle_transcription_finished(self, text):
        # CRITICAL: Set clipboard BEFORE stopping transcription.
        # On Wayland, clipboard is owned by the focused window. If we emit
        # transcription_stopped first, the recording dialog may close before
        # clipboard ownership is established, causing the clipboard to be cleared.
        if text:
            # Use clipboard manager to copy text (signals handle notification)
            self.clipboard_manager.copy_to_clipboard(text)

            # Update tooltip with recognized text
            self.update_tooltip(text)

        # Phase 6: Reset transcribing state via app_state
        # This emits transcription_stopped which triggers dialog hide in popup mode
        self.app_state.stop_transcription()

        # Phase 5: update_transcribing_state() call removed - AudioBridge listens to app_state

        # Close progress window
        self._close_progress_window("after transcription")

    def handle_transcription_error(self, error):
        # Phase 6: Reset transcribing state via app_state
        self.app_state.stop_transcription()

        # Phase 5: update_transcribing_state() call removed - AudioBridge listens to app_state

        self.ui_manager.show_notification(
            self, "Transcription Error", error, self.ui_manager.normal_icon
        )

        # Update tooltip to indicate error
        self.update_tooltip()

        # Close progress window
        self._close_progress_window("after transcription error")

    def toggle_debug_window(self):
        """Toggle debug window visibility"""
        if self.debug_window.isVisible():
            self.debug_window.hide()
            self.debug_action.setText("Show Debug Window")
        else:
            self.debug_window.show()
            self.debug_action.setText("Hide Debug Window")


def setup_application_metadata():
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QCoreApplication.setOrganizationName(ORG_NAME)
    QCoreApplication.setOrganizationDomain("kde.org")


# Global lock manager instance
lock_manager = LockManager(LOCK_FILE_PATH)


def cleanup_lock_file():
    """Clean up lock file when application exits"""
    lock_manager.release_lock()


# Suppress GTK module error messages
os.environ["GTK_MODULES"] = ""


def main():
    async def async_main():
        try:
            # Setup GPU/CUDA if available
            print("Syllablaze - Initializing...")
            gpu_manager = GPUSetupManager()
            gpu_available = gpu_manager.setup()

            # Configure settings based on GPU availability
            settings = Settings()
            gpu_manager.configure_settings(settings)

            # Create application state manager (single source of truth)
            app_state = ApplicationState(settings)
            logger.info("Application state manager created")

            # Check if already running (assuming lock_manager is defined elsewhere)
            if not lock_manager.acquire_lock():
                print("Syllablaze is already running. Only one instance is allowed.")
                return 1

            # Initialize QApplication
            # (Assuming setup_application_metadata is a function defined elsewhere)
            setup_application_metadata()

            # Create UI manager (assuming UIManager is defined)
            ui_manager = UIManager()

            # Show loading window (assuming LoadingWindow is defined)
            loading_window = LoadingWindow()
            loading_window.show()
            app.processEvents()  # Force UI update
            ui_manager.update_loading_status(
                loading_window, "Checking system requirements...", 10
            )

            # Check system tray availability (assuming SyllablazeOrchestrator is defined)
            if not SyllablazeOrchestrator.isSystemTrayAvailable():
                ui_manager.show_error_message(
                    "Error",
                    "System tray is not available. Please ensure your desktop environment supports system tray icons.",
                )
                return 1

            # Create tray icon (assuming SyllablazeOrchestrator is defined)
            tray = SyllablazeOrchestrator(settings, app_state)

            # Connect loading window to tray initialization
            tray.initialization_complete.connect(loading_window.close)

            # Check dependencies (assuming check_dependencies is defined)
            ui_manager.update_loading_status(
                loading_window, "Checking dependencies...", 20
            )
            if not check_dependencies():
                return 1

            # Prevent app from quitting when last window closes
            app.setQuitOnLastWindowClosed(False)

            # Initialize tray asynchronously (assuming initialize_tray is an async function)
            await initialize_tray(tray, loading_window, app, ui_manager)

            # Create a future for application exit
            app_exit_future = asyncio.get_running_loop().create_future()

            def set_exit_result():
                if not app_exit_future.done():
                    app_exit_future.set_result(0)

            app.aboutToQuit.connect(set_exit_result)

            # Wait for the application to exit
            try:
                await app_exit_future
            except RuntimeError as e:
                # Handle case where event loop stops during await
                if "is not the running loop" in str(e):
                    logger.info("Event loop stopped during shutdown await")
                else:
                    raise

            # Disconnect D-Bus bus
            await tray._cleanup_dbus()

            # Clean up (assuming cleanup_lock_file is defined)
            cleanup_lock_file()
            return 0

        except KeyboardInterrupt:
            # Handle Ctrl+C
            print("\nReceived Ctrl+C, exiting...")
            cleanup_lock_file()
            return 0

        except Exception as e:
            # Log error (assuming logger is defined, otherwise use print)
            print(f"Failed to start application: {str(e)}")
            return 1

    # Set up QApplication and event loop
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Suppress qasync's noisy error logging during shutdown
    import logging

    qasync_logger = logging.getLogger("qasync")
    qasync_logger.setLevel(logging.CRITICAL)  # Only show critical errors, not warnings

    # Set custom exception handler to suppress shutdown-related errors
    def custom_exception_handler(loop, context):
        """Custom exception handler that suppresses expected shutdown errors"""
        exception = context.get("exception")
        message = context.get("message", "")

        # Suppress errors that occur during normal shutdown
        if isinstance(exception, RuntimeError):
            if "is not the running loop" in str(exception):
                # This happens during shutdown when callbacks try to run after loop stops
                logger.debug(f"Suppressed shutdown error: {exception}")
                return
            if "Event loop stopped" in str(exception):
                logger.debug(f"Suppressed shutdown error: {exception}")
                return

        # Also suppress "Task was destroyed but it is pending" messages during shutdown
        if "Task was destroyed but it is pending" in message:
            logger.debug(f"Suppressed shutdown message: {message}")
            return

        # For other exceptions, log them normally
        if exception:
            logger.error(
                f"Unhandled exception in event loop: {exception}", exc_info=exception
            )
        else:
            logger.error(f"Unhandled error in event loop: {message}")

    loop.set_exception_handler(custom_exception_handler)

    # Run the asynchronous logic
    try:
        exit_code = loop.run_until_complete(async_main())
    except RuntimeError as e:
        # Handle graceful shutdown when event loop is already stopped
        if "Event loop stopped before Future completed" in str(e):
            logger.info("Event loop stopped during shutdown - this is normal")
            exit_code = 0
        else:
            logger.error(f"Runtime error during event loop: {e}")
            exit_code = 1

    sys.exit(exit_code)


def _initialize_tray_ui(tray, loading_window, app, ui_manager):
    """Initialize basic tray UI components"""
    ui_manager.update_loading_status(loading_window, "Initializing application...", 10)
    tray.initialize()


def _initialize_audio_manager(tray, loading_window, app, ui_manager):
    """Initialize audio recording system"""
    ui_manager.update_loading_status(loading_window, "Initializing audio system...", 25)

    # Create audio manager
    global tray_recorder_instance
    tray.audio_manager = AudioManager(tray.settings)
    tray_recorder_instance = tray

    # Initialize audio manager
    if not tray.audio_manager.initialize():
        ui_manager.show_error_message(
            "Error",
            "Failed to initialize audio system. Please check your audio devices and try again.",
        )
        return False

    return True


def _initialize_transcription_manager(tray, loading_window, app, ui_manager):
    """Initialize transcription system"""
    ui_manager.update_loading_status(
        loading_window, "Initializing transcription system...", 40
    )

    # Create transcription manager
    tray.transcription_manager = TranscriptionManager(tray.settings)

    # Configure optimal settings
    tray.transcription_manager.configure_optimal_settings()

    # Initialize transcription manager
    if not tray.transcription_manager.initialize():
        ui_manager.show_warning_message(
            "No Models Downloaded",
            "No Whisper models are downloaded. The application will start, "
            "but you will need to download a model before you can use "
            "transcription.\n\nPlease go to Settings to download a model.",
        )

    return True


def _connect_signals(tray, loading_window, app, ui_manager):
    """Connect all necessary signals"""
    ui_manager.update_loading_status(
        loading_window, "Setting up signal handlers...", 90
    )

    # Connect audio manager signals
    tray.audio_manager.volume_changing.connect(tray._update_volume_display)
    tray.audio_manager.recording_completed.connect(tray._handle_recording_completed)
    tray.audio_manager.recording_failed.connect(tray.handle_recording_error)

    # Connect audio manager to recording dialog (for volume/samples - new applet handles this directly)
    if tray.recording_dialog:
        tray.recording_dialog.set_audio_manager(tray.audio_manager)
        # Connect bridge signals now that the applet is created
        dismiss_cb = (
            tray.window_visibility_coordinator.on_dialog_dismissed
            if tray.window_visibility_coordinator
            else None
        )
        tray.recording_dialog.connect_bridge_signals(
            toggle_recording_callback=tray.toggle_recording,
            open_settings_callback=tray.toggle_settings,
            dismiss_callback=dismiss_cb,
        )

        # Show applet in persistent mode (KWin properties applied in showEvent)
        if tray.settings:
            applet_mode = tray.settings.get("applet_mode", "popup")
            if applet_mode == "persistent":
                logger.info(
                    "Showing recording dialog after applet creation (persistent mode)"
                )
                tray.app_state.set_recording_dialog_visible(
                    True, source="persistent_mode_startup"
                )
                tray.recording_dialog.show()

    # Connect transcription manager signals
    tray.transcription_manager.transcription_progress.connect(
        tray.update_processing_status
    )
    tray.transcription_manager.transcription_progress_percent.connect(
        tray.update_processing_progress
    )
    tray.transcription_manager.transcription_finished.connect(
        tray.handle_transcription_finished
    )
    tray.transcription_manager.transcription_error.connect(
        tray.handle_transcription_error
    )


async def initialize_tray(tray, loading_window, app, ui_manager):
    """Initialize the application tray with all components"""
    try:
        # Initialize basic tray setup
        _initialize_tray_ui(tray, loading_window, app, ui_manager)

        # Set up D-Bus service
        ui_manager.update_loading_status(
            loading_window, "Setting up D-Bus service...", 15
        )
        try:
            # Create the service in a non-blocking way
            service = SyllaDBusService(tray)

            # Setup D-Bus and get bus connection for shortcuts
            bus = await setup_dbus(service)
            tray._dbus_bus = bus  # store for cleanup on shutdown

        except Exception as e:
            logger.error(f"D-Bus setup failed: {e}")
            bus = None

        # Setup global shortcuts with D-Bus (kglobalaccel)
        if bus:
            ui_manager.update_loading_status(
                loading_window, "Setting up keyboard shortcuts...", 12
            )
            saved_shortcut = tray.settings.get("shortcut", DEFAULT_SHORTCUT)
            try:
                success = await tray.shortcuts.setup_shortcuts(bus, saved_shortcut)
                if success:
                    logger.info(f"Global shortcuts registered: {saved_shortcut}")
                else:
                    logger.warning("Failed to register global shortcuts with KDE")
            except Exception as e:
                logger.warning(f"Failed to register global shortcuts: {e}")
        else:
            logger.warning("No D-Bus connection - shortcuts not registered")

        # Initialize audio manager
        if not _initialize_audio_manager(tray, loading_window, app, ui_manager):
            loading_window.close()
            app.quit()
            return

        # Initialize transcription manager
        if not _initialize_transcription_manager(tray, loading_window, app, ui_manager):
            # Continue anyway, but with limited functionality
            pass

        # Connect signals
        _connect_signals(tray, loading_window, app, ui_manager)

        # Wire popup mode auto-show/hide after all signals are connected
        if hasattr(tray, "window_visibility_coordinator"):
            tray.window_visibility_coordinator.connect_to_app_state()

        # Make tray visible
        ui_manager.update_loading_status(loading_window, "Starting application...", 100)
        tray.setVisible(True)

        # Signal completion
        tray.initialization_complete.emit()

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        ui_manager.show_error_message(
            "Error", f"Failed to initialize application: {str(e)}"
        )
        loading_window.close()
        app.quit()


async def setup_dbus(service):
    """Set up the D-Bus service asynchronously"""
    try:
        bus = await MessageBus().connect()
        bus.export("/org/kde/syllablaze", service)
        await bus.request_name("org.kde.syllablaze")
        logger.info("D-Bus service registered successfully")
        return bus
    except Exception as e:
        logger.error(f"D-Bus setup failed: {e}")
        return None


if __name__ == "__main__":
    # Create QApplication first
    app = QApplication(sys.argv)

    # Setup QApplication with asyncio integration
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Start the application properly
    with loop:
        loop.run_until_complete(main())
