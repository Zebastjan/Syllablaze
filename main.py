# Set environment variables to suppress Jack errors before any imports
import os
# Tell Jack not to start if not available
os.environ['JACK_NO_AUDIO_RESERVATION'] = '1'
os.environ['JACK_NO_START_SERVER'] = '1'
# Explicitly ignore Jack - we'll use ALSA or PulseAudio instead
os.environ['AUDIODEV'] = 'null'

import sys
from PyQt6.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
from PyQt6.QtGui import QIcon, QAction
import logging
from settings_window import SettingsWindow
from progress_window import ProgressWindow
from processing_window import ProcessingWindow
from recorder import AudioRecorder
from transcriber import WhisperTranscriber
from loading_window import LoadingWindow
from PyQt6.QtCore import pyqtSignal
import warnings
import ctypes
from shortcuts import GlobalShortcuts
from settings import Settings
from constants import APP_NAME, APP_VERSION, DEFAULT_WHISPER_MODEL, ORG_NAME
from whisper_model_manager import get_model_info
# from mic_debug import MicDebugWindow

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log that Jack errors can be safely ignored
logger.info("Note: Jack server errors can be safely ignored - using ALSA/PulseAudio instead")

# Audio error handling is now done in recorder.py
# This comment is kept for documentation purposes

def check_dependencies():
    required_packages = ['whisper', 'pyaudio', 'keyboard']
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

class TrayRecorder(QSystemTrayIcon):
    initialization_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Initialize basic state
        self.recording = False
        self.settings_window = None
        self.progress_window = None
        self.processing_window = None
        self.recorder = None
        self.transcriber = None
        
        # Create debug window but don't show it
        # self.debug_window = MicDebugWindow()
        
        # Set tooltip
        self.setToolTip(f"{APP_NAME} {APP_VERSION}")
        
        # Enable activation by left click
        self.activated.connect(self.on_activate)
        
        # Add shortcuts handler
        self.shortcuts = GlobalShortcuts()
        self.shortcuts.start_recording_triggered.connect(self.start_recording)
        self.shortcuts.stop_recording_triggered.connect(self.stop_recording)

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
        
        # Setup global shortcuts
        if not self.shortcuts.setup_shortcuts():
            logger.warning("Failed to register global shortcuts")
            
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
        
        # Add debug window action
        # self.debug_action = QAction("Show Debug Window", menu)
        # self.debug_action.triggered.connect(self.toggle_debug_window)
        # menu.addAction(self.debug_action)
        
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
            if self.recorder:
                try:
                    self.recorder.stop_recording()
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
                self.progress_window.stop_clicked.connect(self.stop_recording)
            self.progress_window.show()
            
            # Start recording
            self.record_action.setText("Stop Recording")
            self.setIcon(self.recording_icon)
            self.recorder.start_recording()

    def stop_recording(self):
        """Handle stopping the recording and starting processing"""
        if not self.recording:
            return
        
        logger.info("TrayRecorder: Stopping recording")
        self.toggle_recording()  # This is now safe since toggle_recording handles everything

    def toggle_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
            self.settings_window.shortcuts_changed.connect(self.update_shortcuts)
        
        if self.settings_window.isVisible():
            self.settings_window.hide()
        else:
            # Make sure the window is maximized
            self.settings_window.showMaximized()
            # Bring to front and activate
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            
    def update_tooltip(self, recognized_text=None):
        """Update the tooltip with app name, version, and model information"""
        settings = Settings()
        model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
        tooltip = f"{APP_NAME} {APP_VERSION}\nmodel: {model_name}"
        
        # Add recognized text to tooltip if provided
        if recognized_text:
            # Truncate text if it's too long
            max_length = 100
            if len(recognized_text) > max_length:
                recognized_text = recognized_text[:max_length] + "..."
            tooltip += f"\nRecognized: {recognized_text}"
            
        self.setToolTip(tooltip)
    
    def update_shortcuts(self, start_key, stop_key):
        """Update global shortcuts"""
        if self.shortcuts.setup_shortcuts(start_key, stop_key):
            self.showMessage("Shortcuts Updated",
                           f"Start: {start_key}\nStop: {stop_key}",
                           self.normal_icon)

    def on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            self.toggle_recording()

    def quit_application(self):
        try:
            # Cleanup recorder
            if self.recorder:
                self.recorder.cleanup()
                self.recorder = None
            
            # Close all windows
            if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.isVisible():
                self.settings_window.close()
                
            if hasattr(self, 'progress_window') and self.progress_window and self.progress_window.isVisible():
                self.progress_window.close()
                
            # Stop recording if active
            if self.recording:
                self.stop_recording()
                
            # Wait for any running threads to finish
            if hasattr(self, 'transcriber') and self.transcriber:
                if hasattr(self.transcriber, 'worker') and self.transcriber.worker:
                    if self.transcriber.worker.isRunning():
                        logger.info("Waiting for transcription worker to finish...")
                        self.transcriber.worker.wait(1000)  # Wait up to 1 second
                        
            # Quit the application
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            # Force quit if there was an error
            QApplication.exit(1)

    def update_volume_meter(self, value):
        # Update debug window first
        if hasattr(self, 'debug_window'):
            self.debug_window.update_values(value)
            
        # Then update volume meter as before
        if self.progress_window and self.recording:
            self.progress_window.update_volume(value)
    
    def handle_recording_finished(self, audio_file):
        """Called when recording is saved to file"""
        logger.info("TrayRecorder: Recording finished, starting transcription")
        
        # Ensure progress window is in processing mode
        if self.progress_window:
            self.progress_window.set_processing_mode()
            self.progress_window.set_status("Starting transcription...")
        
        if self.transcriber:
            self.transcriber.transcribe_file(audio_file)
        else:
            logger.error("Transcriber not initialized")
            if self.progress_window:
                self.progress_window.close()
                self.progress_window = None
            
            # Show notification instead of dialog
            self.showMessage("Error",
                           "Transcriber not initialized",
                           self.normal_icon)
    
    def handle_recording_error(self, error):
        """Handle recording errors"""
        logger.error(f"TrayRecorder: Recording error: {error}")
        
        # Show notification instead of dialog
        self.showMessage("Recording Error",
                       error,
                       self.normal_icon)
        
        self.stop_recording()
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None
    
    def update_processing_status(self, status):
        if self.progress_window:
            self.progress_window.set_status(status)
            
    def update_processing_progress(self, percent):
        if self.progress_window:
            self.progress_window.update_progress(percent)
    
    def handle_transcription_finished(self, text):
        if text:
            # Copy text to clipboard
            QApplication.clipboard().setText(text)
            
            # Truncate text for notification if it's too long
            display_text = text
            if len(text) > 100:
                display_text = text[:100] + "..."
                
            # Show notification with the transcribed text
            self.showMessage("Transcription Complete",
                           f"{display_text}",
                           self.normal_icon)
            
            # Update tooltip with recognized text
            self.update_tooltip(text)
        
        # Close the progress window
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None
    
    def handle_transcription_error(self, error):
        self.showMessage("Transcription Error",
                       error,
                       self.normal_icon)
        
        # Update tooltip to indicate error
        self.update_tooltip()
        
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None

    def start_recording(self):
        """Start a new recording"""
        if not self.recording:
            self.toggle_recording()
            
    def stop_recording(self):
        """Stop current recording"""
        if self.recording:
            self.toggle_recording()

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

def main():
    try:
        # Set up signal handling for CTRL-C
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        app = QApplication(sys.argv)
        setup_application_metadata()
        
        # Show loading window first
        loading_window = LoadingWindow()
        loading_window.show()
        app.processEvents()  # Force update of UI
        loading_window.set_status("Checking system requirements...")
        app.processEvents()  # Force update of UI
        
        # Check if system tray is available
        if not TrayRecorder.isSystemTrayAvailable():
            QMessageBox.critical(None, "Error",
                "System tray is not available. Please ensure your desktop environment supports system tray icons.")
            return 1
        
        # Create tray icon but don't initialize yet
        tray = TrayRecorder()
        
        # Connect loading window to tray initialization
        tray.initialization_complete.connect(loading_window.close)
        
        # Check dependencies in background
        loading_window.set_status("Checking dependencies...")
        app.processEvents()  # Force update of UI
        if not check_dependencies():
            return 1
        
        # Ensure the application doesn't quit when last window is closed
        app.setQuitOnLastWindowClosed(False)
        
        # Initialize tray in background
        QTimer.singleShot(100, lambda: initialize_tray(tray, loading_window, app))
        
        return app.exec()
        
    except Exception as e:
        logger.exception("Failed to start application")
        QMessageBox.critical(None, "Error",
            f"Failed to start application: {str(e)}")
        return 1

def initialize_tray(tray, loading_window, app):
    try:
        # Initialize basic tray setup
        loading_window.set_status("Initializing application...")
        loading_window.set_progress(10)
        app.processEvents()
        tray.initialize()
        
        # Initialize recorder
        loading_window.set_status("Initializing audio system...")
        loading_window.set_progress(25)
        app.processEvents()
        tray.recorder = AudioRecorder()
        
        # Initialize transcriber
        settings = Settings()
        model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
        
        # Check if model is downloaded
        try:
            model_info, _ = get_model_info()
            if model_name in model_info and not model_info[model_name]['is_downloaded']:
                loading_window.set_status(f"Whisper model '{model_name}' is not downloaded. Using default model.")
                loading_window.set_progress(40)
                app.processEvents()
                # Set model to default if current model is not downloaded
                settings.set('model', DEFAULT_WHISPER_MODEL)
                model_name = DEFAULT_WHISPER_MODEL
        except Exception as model_error:
            logger.error(f"Error checking model info: {model_error}")
            loading_window.set_status("Error checking model info. Using default model.")
            loading_window.set_progress(40)
            app.processEvents()
            # Set model to default if there was an error
            settings.set('model', DEFAULT_WHISPER_MODEL)
            model_name = DEFAULT_WHISPER_MODEL
        
        loading_window.set_status(f"Loading Whisper model: {model_name}")
        loading_window.set_progress(50)
        app.processEvents()
        
        try:
            tray.transcriber = WhisperTranscriber()
            loading_window.set_progress(80)
            app.processEvents()
        except Exception as e:
            logger.error(f"Failed to initialize transcriber: {e}")
            QMessageBox.critical(None, "Error",
                f"Failed to load Whisper model: {str(e)}\n\nPlease check Settings to download the model.")
            loading_window.set_progress(80)
            app.processEvents()
            # Create transcriber anyway, it will handle errors during transcription
            tray.transcriber = WhisperTranscriber()
        
        # Connect signals
        loading_window.set_status("Setting up signal handlers...")
        loading_window.set_progress(90)
        app.processEvents()
        tray.recorder.volume_updated.connect(tray.update_volume_meter)
        tray.recorder.recording_finished.connect(tray.handle_recording_finished)
        tray.recorder.recording_error.connect(tray.handle_recording_error)
        
        tray.transcriber.transcription_progress.connect(tray.update_processing_status)
        tray.transcriber.transcription_progress_percent.connect(tray.update_processing_progress)
        tray.transcriber.transcription_finished.connect(tray.handle_transcription_finished)
        tray.transcriber.transcription_error.connect(tray.handle_transcription_error)
        
        # Make tray visible
        loading_window.set_status("Starting application...")
        loading_window.set_progress(100)
        app.processEvents()
        
        # Make tray visible
        tray.setVisible(True)
        
        # Signal completion
        tray.initialization_complete.emit()
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        QMessageBox.critical(None, "Error", f"Failed to initialize application: {str(e)}")
        loading_window.close()
        # Ensure the application can be closed with CTRL+C
        app.quit()

if __name__ == "__main__":
    sys.exit(main()) 