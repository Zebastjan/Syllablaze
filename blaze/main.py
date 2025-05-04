import os
import sys
from PyQt6.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import QTimer, QCoreApplication
from PyQt6.QtGui import QIcon, QAction
import logging
from blaze.settings_window import SettingsWindow
from blaze.progress_window import ProgressWindow
from blaze.loading_window import LoadingWindow
from PyQt6.QtCore import pyqtSignal
from blaze.settings import Settings
from blaze.constants import (
    APP_NAME, APP_VERSION, DEFAULT_WHISPER_MODEL, ORG_NAME, VALID_LANGUAGES, LOCK_FILE_PATH
)
from blaze.managers.ui_manager import UIManager
from blaze.managers.lock_manager import LockManager
from blaze.managers.audio_manager import AudioManager
from blaze.managers.transcription_manager import TranscriptionManager

import asyncio
from dbus_next.service import ServiceInterface, method
from dbus_next.aio import MessageBus
import qasync

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio error handling is now done in recorder.py
# This comment is kept for documentation purposes

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
    required_packages = ['faster_whisper', 'pyaudio', 'keyboard']
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

class ApplicationTrayIcon(QSystemTrayIcon):
    initialization_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Initialize basic state
        
        # Initialize basic state
        self.recording = False
        self.settings_window = None
        self.progress_window = None
        self.processing_window = None
        
        # Initialize managers
        self.ui_manager = UIManager()
        self.audio_manager = None
        self.transcription_manager = None

        # Set tooltip
        self.setToolTip(f"{APP_NAME} {APP_VERSION}")
        
        # Enable activation by left click
        self.activated.connect(self.on_activate)

    def initialize(self):
        """Initialize the tray recorder after showing loading window"""
        # Set application icon
        self.app_icon = QIcon.fromTheme("syllablaze")
        if self.app_icon.isNull():
            # Try to load from local path
            local_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "syllablaze.png")
            if os.path.exists(local_icon_path):
                self.app_icon = QIcon(local_icon_path)
            else:
                # Fallback to theme icons if custom icon not found
                self.app_icon = QIcon.fromTheme("media-record")
                logger.warning("Could not load syllablaze icon, using system theme icon")
            
        # Set the icon for both app and tray
        QApplication.instance().setWindowIcon(self.app_icon)
        self.setIcon(self.app_icon)
        
        # Use app icon for normal state and theme icon for recording
        self.normal_icon = self.app_icon
        self.recording_icon = QIcon.fromTheme("media-playback-stop")
        
        # Create menu
        self.setup_menu()
            
        # Initialize tooltip with model information
        self.update_tooltip()

    def setup_menu(self):
        menu = QMenu()
        
        # Add recording action
        self.record_action = QAction("Start Recording", menu)
        self.record_action.triggered.connect(self.toggle_recording)
        menu.addAction(self.record_action)
        
        # Add settings action
        self.settings_action = QAction("Settings", menu)
        self.settings_action.triggered.connect(self.toggle_settings)
        menu.addAction(self.settings_action)

        # Add separator before quit
        menu.addSeparator()
        
        # Add quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(quit_action)
        
        # Set the context menu
        self.setContextMenu(menu)

    @staticmethod
    def isSystemTrayAvailable():
        return QSystemTrayIcon.isSystemTrayAvailable()

    def toggle_recording(self):
        """Toggle recording state with improved resilience to rapid clicks"""
        # Use a lock to prevent concurrent execution of this method
        if hasattr(self, '_recording_lock') and self._recording_lock:
            logger.info("Recording toggle already in progress, ignoring request")
            return
            
        # Set lock
        self._recording_lock = True
        
        try:
            # Check if transcriber is properly initialized
            if not self.recording and (not hasattr(self, 'transcription_manager') \
                or not self.transcription_manager \
                or not hasattr(self.transcription_manager.transcriber, 'model') \
                or not self.transcription_manager.transcriber.model):
                # Transcriber is not properly initialized, show a message
                self.ui_manager.show_notification(
                    self,
                    "No Models Downloaded",
                    "No Whisper models are downloaded. Please go to Settings to download a model.",
                    self.normal_icon
                )
                # Open settings window to allow user to download a model
                self.toggle_settings()
                return
                
            # Get current state before changing it (for logging)
            current_state = "recording" if self.recording else "not recording"
            new_state = "stop recording" if self.recording else "start recording"
            logger.info(f"Toggle recording: {current_state} -> {new_state}")
                
            if self.recording:
                # Stop recording
                # Update UI first to give immediate feedback
                self.record_action.setText("Start Recording")
                self.setIcon(self.normal_icon)
                
                # Update progress window before stopping recording
                if self.progress_window:
                    self.progress_window.set_processing_mode()
                    self.progress_window.set_status("Processing audio...")
                
                # Stop the actual recording
                if self.audio_manager:
                    try:
                        # Only change recording state after successful stop
                        result = self.audio_manager.stop_recording()
                        if result:
                            self.recording = False
                            logger.info("Recording stopped successfully")
                        else:
                            # Revert UI if stop failed
                            logger.error("Failed to stop recording")
                            self.record_action.setText("Stop Recording")
                            self.setIcon(self.recording_icon)
                    except Exception as e:
                        logger.error(f"Error stopping recording: {e}")
                        # Revert UI if exception occurred
                        self.record_action.setText("Stop Recording")
                        self.setIcon(self.recording_icon)
                        if self.progress_window:
                            self.progress_window.close()
                            self.progress_window = None
                else:
                    # No audio manager, just update state
                    self.recording = False
            else:
                # Start recording
                # Always create a fresh progress window
                # Close any existing window first
                if self.progress_window:
                    self.ui_manager.safely_close_window(self.progress_window, "before new recording")
                    self.progress_window = None
                
                # Create a new progress window
                self.progress_window = ProgressWindow("Voice Recording")
                self.progress_window.stop_clicked.connect(self._stop_recording)
                self.progress_window.show()
                
                # Update UI to give immediate feedback
                self.record_action.setText("Stop Recording")
                self.setIcon(self.recording_icon)
                
                # Start the actual recording
                if self.audio_manager:
                    try:
                        # Only change recording state after successful start
                        result = self.audio_manager.start_recording()
                        if result:
                            self.recording = True
                            logger.info("Recording started successfully")
                        else:
                            # Revert UI if start failed
                            logger.error("Failed to start recording")
                            self.record_action.setText("Start Recording")
                            self.setIcon(self.normal_icon)
                            if self.progress_window:
                                self.progress_window.close()
                                self.progress_window = None
                    except Exception as e:
                        logger.error(f"Error starting recording: {e}")
                        # Revert UI if exception occurred
                        self.record_action.setText("Start Recording")
                        self.setIcon(self.normal_icon)
                        if self.progress_window:
                            self.progress_window.close()
                            self.progress_window = None
                else:
                    # No audio manager, just update state
                    self.recording = True
        finally:
            # Always release the lock
            self._recording_lock = False

    def _stop_recording(self):
        """Internal method to stop recording and start processing"""
        if not self.recording:
            return
        
        logger.info("ApplicationTrayIcon: Stopping recording")
        self.toggle_recording()  # This is now safe since toggle_recording handles everything

    def toggle_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
        
        if self.settings_window.isVisible():
            self.settings_window.hide()
        else:
            # Show the window (not maximized)
            self.settings_window.show()
            # Bring to front and activate
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            
    def update_tooltip(self, recognized_text=None):
        """Update the tooltip with app name, version, model and language information"""
        import sys
        
        settings = Settings()
        model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
        language_code = settings.get('language', 'auto')
        
        # Get language display name from VALID_LANGUAGES if available
        if language_code in VALID_LANGUAGES:
            language_display = f"Language: {VALID_LANGUAGES[language_code]}"
        else:
            language_display = "Language: auto-detect" if language_code == 'auto' else f"Language: {language_code}"
        
        tooltip = f"{APP_NAME} {APP_VERSION}\nModel: {model_name}\n{language_display}"
        
        # Add recognized text to tooltip if provided
        if recognized_text:
            # Truncate text if it's too long
            max_length = 100
            if len(recognized_text) > max_length:
                recognized_text = recognized_text[:max_length] + "..."
            tooltip += f"\nRecognized: {recognized_text}"
        
        # Print tooltip info to console with flush
        print(f"TOOLTIP UPDATE: MODEL={model_name}, {language_display}", flush=True)
        sys.stdout.flush()
            
        self.setToolTip(tooltip)
    
    # Removed update_shortcuts method as part of keyboard shortcut functionality removal

    def on_activate(self, reason):
        """Handle tray icon activation with improved resilience"""
        # Ignore activations if we're already processing a click
        if hasattr(self, '_activation_lock') and self._activation_lock:
            logger.info("Activation already in progress, ignoring request")
            return
            
        # Set lock
        self._activation_lock = True
        
        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
                logger.info("Tray icon left-clicked")
                
                # Check if we're in the middle of processing a recording
                if hasattr(self, 'progress_window') and self.progress_window and self.progress_window.isVisible():
                    if not self.recording and getattr(self.progress_window, 'processing', False):
                        logger.info("Processing in progress, ignoring activation")
                        return
                
                # Check if transcriber is properly initialized
                if hasattr(self, 'transcription_manager') and self.transcription_manager \
                        and hasattr(self.transcription_manager.transcriber, 'model') \
                        and self.transcription_manager.transcriber.model:
                    # Transcriber is properly initialized, proceed with recording
                    self.toggle_recording()
                else:
                    # Transcriber is not properly initialized, show a message
                    self.ui_manager.show_notification(
                        self,
                        "No Models Downloaded",
                        "No Whisper models are downloaded. Please go to Settings to download a model.",
                        self.normal_icon
                    )
                    # Open settings window to allow user to download a model
                    self.toggle_settings()
        finally:
            # Always release the lock
            self._activation_lock = False

    def quit_application(self):
        try:
            self._cleanup_recorder()
            self._close_windows()
            self._stop_active_recording()
            self._wait_for_threads()
            
            logger.info("Application shutdown complete, exiting...")
            
            # Explicitly quit the application
            QApplication.instance().quit()
            
            # Force exit after a short delay to ensure cleanup
            QTimer.singleShot(500, lambda: sys.exit(0))
                
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

    def _close_windows(self):
        # Close settings window
        if hasattr(self, 'settings_window') and self.settings_window:
            self.ui_manager.safely_close_window(self.settings_window, "settings")
            
        # Close progress window
        if hasattr(self, 'progress_window') and self.progress_window:
            self.ui_manager.safely_close_window(self.progress_window, "progress")

    def _stop_active_recording(self):
        if self.recording:
            try:
                self._stop_recording()
            except Exception as rec_error:
                logger.error(f"Error stopping recording: {rec_error}")

    def _wait_for_threads(self):
        if hasattr(self, 'transcription_manager') and self.transcription_manager:
            try:
                self.transcription_manager.cleanup()
            except Exception as thread_error:
                logger.error(f"Error waiting for transcription worker: {thread_error}")

    def _update_volume_display(self, volume_level):
        """Update the UI with current volume level"""
        if self.progress_window and self.recording:
            self.progress_window.update_volume(volume_level)
    
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
        logger.info("ApplicationTrayIcon: Recording processed, starting transcription")
        
        # Ensure progress window is in processing mode
        if self.progress_window:
            self.progress_window.set_processing_mode()
            self.progress_window.set_status("Starting transcription...")
        else:
            logger.error("Progress window not available when recording completed")
        
        try:
            if not self.transcription_manager:
                raise RuntimeError("Transcriber not initialized")
            logger.info(f"Transcriber ready: {self.transcription_manager}")
            
            if not hasattr(self.transcription_manager.transcriber, 'model') \
               or not self.transcription_manager.transcriber.model:
                raise RuntimeError("Whisper model not loaded")
                
            self.transcription_manager.transcribe_audio(normalized_audio_data)
            
        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            if self.progress_window:
                self.progress_window.close()
                self.progress_window = None
            
            self.ui_manager.show_notification(
                self,
                "Error",
                f"Failed to start transcription: {str(e)}",
                self.normal_icon
            )
    
    def handle_recording_error(self, error):
        """Handle recording errors"""
        logger.error(f"ApplicationTrayIcon: Recording error: {error}")
        
        # Show notification instead of dialog
        self.ui_manager.show_notification(
            self,
            "Recording Error",
            error,
            self.normal_icon
        )
        
        self._stop_recording()
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None
    
    def update_processing_status(self, status):
        if self.progress_window:
            self.progress_window.set_status(status)
            
    def update_processing_progress(self, percent):
        if self.progress_window:
            self.progress_window.update_progress(percent)
    
    def _close_progress_window(self, context=""):
        """Helper method to safely close progress window"""
        if self.progress_window:
            self.ui_manager.safely_close_window(self.progress_window, f"progress {context}")
            # Explicitly set to None to force recreation on next recording
            self.progress_window = None
        else:
            logger.warning(f"Progress window not found when trying to close {context}".strip())
    
    def handle_transcription_finished(self, text):
        if text:
            # Copy text to clipboard
            QApplication.clipboard().setText(text)
            
            # Truncate text for notification if it's too long
            display_text = text
            if len(text) > 100:
                display_text = text[:100] + "..."
                
            # Show notification with the transcribed text
            self.ui_manager.show_notification(
                self,
                "Transcription Complete",
                display_text,
                self.normal_icon
            )
            
            # Update tooltip with recognized text
            self.update_tooltip(text)
        
        # Close progress window
        self._close_progress_window("after transcription")
    
    def handle_transcription_error(self, error):
        self.ui_manager.show_notification(
            self,
            "Transcription Error",
            error,
            self.normal_icon
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
os.environ['GTK_MODULES'] = ''

def main():
    async def async_main():
        try:
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
            ui_manager.update_loading_status(loading_window, "Checking system requirements...", 10)
            
            # Check system tray availability (assuming ApplicationTrayIcon is defined)
            if not ApplicationTrayIcon.isSystemTrayAvailable():
                ui_manager.show_error_message(
                    "Error",
                    "System tray is not available. Please ensure your desktop environment supports system tray icons."
                )
                return 1
            
            # Create tray icon (assuming ApplicationTrayIcon is defined)
            tray = ApplicationTrayIcon()
            
            # Connect loading window to tray initialization
            tray.initialization_complete.connect(loading_window.close)
            
            # Check dependencies (assuming check_dependencies is defined)
            ui_manager.update_loading_status(loading_window, "Checking dependencies...", 20)
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
            await app_exit_future

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
    
    # Run the asynchronous logic
    exit_code = loop.run_until_complete(async_main())
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
    tray.audio_manager = AudioManager(Settings())
    tray_recorder_instance = tray
    
    # Initialize audio manager
    if not tray.audio_manager.initialize():
        ui_manager.show_error_message(
            "Error",
            "Failed to initialize audio system. Please check your audio devices and try again."
        )
        return False
    
    return True

def _initialize_transcription_manager(tray, loading_window, app, ui_manager):
    """Initialize transcription system"""
    ui_manager.update_loading_status(loading_window, "Initializing transcription system...", 40)
    
    # Create transcription manager
    tray.transcription_manager = TranscriptionManager(Settings())
    
    # Configure optimal settings
    tray.transcription_manager.configure_optimal_settings()
    
    # Initialize transcription manager
    if not tray.transcription_manager.initialize():
        ui_manager.show_warning_message(
            "No Models Downloaded",
            "No Whisper models are downloaded. The application will start, but you will need to download a model before you can use transcription.\n\n"
            "Please go to Settings to download a model."
        )
    
    return True

def _connect_signals(tray, loading_window, app, ui_manager):
    """Connect all necessary signals"""
    ui_manager.update_loading_status(loading_window, "Setting up signal handlers...", 90)
    
    # Connect audio manager signals
    tray.audio_manager.volume_changing.connect(tray._update_volume_display)
    tray.audio_manager.recording_completed.connect(tray._handle_recording_completed)
    tray.audio_manager.recording_failed.connect(tray.handle_recording_error)
    
    # Connect transcription manager signals
    tray.transcription_manager.transcription_progress.connect(tray.update_processing_status)
    tray.transcription_manager.transcription_progress_percent.connect(tray.update_processing_progress)
    tray.transcription_manager.transcription_finished.connect(tray.handle_transcription_finished)
    tray.transcription_manager.transcription_error.connect(tray.handle_transcription_error)

async def initialize_tray(tray, loading_window, app, ui_manager):
    """Initialize the application tray with all components"""
    try:
        # Initialize basic tray setup
        _initialize_tray_ui(tray, loading_window, app, ui_manager)
        
        # Set up D-Bus service
        ui_manager.update_loading_status(loading_window, "Setting up D-Bus service...", 15)
        try:
            # Create the service in a non-blocking way
            service = SyllaDBusService(tray)
            
            # Directly await the setup
            await setup_dbus(service)
            
        except Exception as e:
            logger.error(f"D-Bus setup failed: {e}")

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
        
        # Make tray visible
        ui_manager.update_loading_status(loading_window, "Starting application...", 100)
        tray.setVisible(True)
        
        # Signal completion
        tray.initialization_complete.emit()
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        ui_manager.show_error_message(
            "Error",
            f"Failed to initialize application: {str(e)}"
        )
        loading_window.close()
        app.quit()

async def setup_dbus(service):
    """Set up the D-Bus service asynchronously"""
    try:
        bus = await MessageBus().connect()
        bus.export('/org/kde/syllablaze', service)
        await bus.request_name('org.kde.syllablaze')
        logger.info("D-Bus service registered successfully")
    except Exception as e:
        logger.error(f"D-Bus setup failed: {e}")

if __name__ == "__main__":
    # Global variable to store the tray recorder instance
    tray_recorder_instance = None

    # Create QApplication first
    app = QApplication(sys.argv)

    # Setup QApplication with asyncio integration
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Start the application properly
    with loop:
        loop.run_until_complete(main())
