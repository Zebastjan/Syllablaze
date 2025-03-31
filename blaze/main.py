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
    APP_NAME, APP_VERSION, DEFAULT_WHISPER_MODEL, ORG_NAME, VALID_LANGUAGES, LOCK_FILE_PATH,
    DEFAULT_BEAM_SIZE, DEFAULT_VAD_FILTER, DEFAULT_WORD_TIMESTAMPS
)
from blaze.managers.ui_manager import UIManager
from blaze.managers.lock_manager import LockManager
from blaze.managers.audio_manager import AudioManager
from blaze.managers.transcription_manager import TranscriptionManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio error handling is now done in recorder.py
# This comment is kept for documentation purposes

def configure_faster_whisper():
    """Configure optimal settings for Faster Whisper based on hardware"""
    settings = Settings()
    
    # Check if this is the first run with Faster Whisper settings
    if settings.get('compute_type') is None:
        # Check for GPU support
        try:
            import torch
            has_gpu = torch.cuda.is_available()
        except ImportError:
            has_gpu = False
        except Exception:
            has_gpu = False
            
        if has_gpu:
            # Configure for GPU
            settings.set('device', 'cuda')
            settings.set('compute_type', 'float16')  # Good balance of speed and accuracy
        else:
            # Configure for CPU
            settings.set('device', 'cpu')
            settings.set('compute_type', 'int8')  # Best performance on CPU
            
        # Set other defaults
        settings.set('beam_size', DEFAULT_BEAM_SIZE)
        settings.set('vad_filter', DEFAULT_VAD_FILTER)
        settings.set('word_timestamps', DEFAULT_WORD_TIMESTAMPS)
        
        logger.info("Faster Whisper configured with optimal settings for your hardware.")
        print("Faster Whisper configured with optimal settings for your hardware.")

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

# Global variable to store the tray recorder instance
tray_recorder_instance = None

def get_tray_recorder():
    """Get the global tray recorder instance"""
    return tray_recorder_instance

def update_tray_tooltip():
    """Update the tray tooltip"""
    if tray_recorder_instance:
        tray_recorder_instance.update_tooltip()

class ApplicationTrayIcon(QSystemTrayIcon):
    initialization_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Store the instance in the global variable
        global tray_recorder_instance
        tray_recorder_instance = self
        
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
        # Check if transcriber is properly initialized
        if not self.recording and (not hasattr(self, 'transcription_manager') or not self.transcription_manager or
                                  not hasattr(self.transcription_manager.transcriber, 'model') or not self.transcription_manager.transcriber.model):
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
            
        if self.recording:
            # Stop recording
            self.recording = False
            self.record_action.setText("Start Recording")
            self.setIcon(self.normal_icon)
            
            # Update progress window before stopping recording
            if self.progress_window:
                self.progress_window.set_processing_mode()
                self.progress_window.set_status("Processing audio...")
            
            # Stop the actual recording
            if self.audio_manager:
                try:
                    self.audio_manager.stop_recording()
                except Exception as e:
                    logger.error(f"Error stopping recording: {e}")
                    if self.progress_window:
                        self.progress_window.close()
                        self.progress_window = None
                    return
        else:
            # Start recording
            self.recording = True
            # Show progress window
            if not self.progress_window:
                self.progress_window = ProgressWindow("Voice Recording")
                self.progress_window.stop_clicked.connect(self._stop_recording)
            self.progress_window.show()
            
            # Start recording
            self.record_action.setText("Stop Recording")
            self.setIcon(self.recording_icon)
            self.audio_manager.start_recording()

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
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            # Check if transcriber is properly initialized
            if hasattr(self, 'transcription_manager') and self.transcription_manager and hasattr(self.transcription_manager.transcriber, 'model') and self.transcription_manager.transcriber.model:
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
            
            if not hasattr(self.transcription_manager.transcriber, 'model') or not self.transcription_manager.transcriber.model:
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

def check_already_running():
    """Check if Syllablaze is already running using a file lock mechanism"""
    # Try to acquire the lock
    if lock_manager.acquire_lock():
        # Lock acquired, no other instance is running
        return False
    else:
        # Lock not acquired, another instance is running
        return True

def cleanup_lock_file():
    """Clean up lock file when application exits"""
    lock_manager.release_lock()

# Suppress GTK module error messages
os.environ['GTK_MODULES'] = ''

def main():
    import sys
    
    # We won't use signal handlers since they don't seem to work with Qt
    # Instead, we'll use a more direct approach
    
    try:
        
        # Check if already running
        if check_already_running():
            print("Syllablaze is already running. Only one instance is allowed.")
            # Exit gracefully without trying to show a QMessageBox
            return 1
            
        # Initialize QApplication after checking for another instance
        app = QApplication(sys.argv)
        setup_application_metadata()
        
        # Create UI manager
        ui_manager = UIManager()
        
        # Show loading window first
        loading_window = LoadingWindow()
        loading_window.show()
        app.processEvents()  # Force update of UI
        ui_manager.update_loading_status(loading_window, "Checking system requirements...", 10)
        
        # Check if system tray is available
        if not ApplicationTrayIcon.isSystemTrayAvailable():
            ui_manager.show_error_message(
                "Error",
                "System tray is not available. Please ensure your desktop environment supports system tray icons."
            )
            return 1
        
        # Create tray icon but don't initialize yet
        tray = ApplicationTrayIcon()
        
        # Connect loading window to tray initialization
        tray.initialization_complete.connect(loading_window.close)
        
        # Check dependencies in background
        ui_manager.update_loading_status(loading_window, "Checking dependencies...", 20)
        if not check_dependencies():
            return 1
        
        # Ensure the application doesn't quit when last window is closed
        app.setQuitOnLastWindowClosed(False)
        
        # Initialize tray in background
        QTimer.singleShot(100, lambda: initialize_tray(tray, loading_window, app, ui_manager))
        
        # Instead of using app.exec(), we'll use a custom event loop
        # that allows us to check for keyboard interrupts
        try:
            # Start the Qt event loop
            exit_code = app.exec()
            # Clean up before exiting
            cleanup_lock_file()
            return exit_code
        except KeyboardInterrupt:
            # This will catch Ctrl+C
            print("\nReceived Ctrl+C, exiting...")
            cleanup_lock_file()
            return 0
        
    except Exception as e:
        logger.exception("Failed to start application")
        QMessageBox.critical(None, "Error",
            f"Failed to start application: {str(e)}")
        return 1

def _initialize_tray_ui(tray, loading_window, app, ui_manager):
    """Initialize basic tray UI components"""
    ui_manager.update_loading_status(loading_window, "Initializing application...", 10)
    tray.initialize()

def _initialize_audio_manager(tray, loading_window, app, ui_manager):
    """Initialize audio recording system"""
    ui_manager.update_loading_status(loading_window, "Initializing audio system...", 25)
    
    # Create audio manager
    tray.audio_manager = AudioManager(Settings())
    
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

def initialize_tray(tray, loading_window, app, ui_manager):
    """Initialize the application tray with all components"""
    try:
        # Initialize basic tray setup
        _initialize_tray_ui(tray, loading_window, app, ui_manager)
        
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

if __name__ == "__main__":
    sys.exit(main())