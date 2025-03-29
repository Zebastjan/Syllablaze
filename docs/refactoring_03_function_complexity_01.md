# Function/Method Length and Complexity - Part 1/3

## 6.1. Long Methods in main.py

**Issue:** Several methods in `main.py` are too long and complex, particularly `initialize_tray()` and `quit_application()`.

**Example:**
```python
# In main.py
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