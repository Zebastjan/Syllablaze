# Function/Method Length and Complexity - Part 2/3

**Solution:** Break down long methods into smaller, focused methods:

```python
# For initialize_tray
def initialize_tray(tray, loading_window, app):
    try:
        # Initialize basic tray setup
        _initialize_tray_ui(tray, loading_window, app)
        
        # Initialize recorder
        _initialize_recorder(tray, loading_window, app)
        
        # Initialize transcriber
        _initialize_transcriber(tray, loading_window, app)
        
        # Connect signals
        _connect_signals(tray, loading_window, app)
        
        # Make tray visible
        _finalize_tray_initialization(tray, loading_window)
        
    except Exception as e:
        _handle_initialization_error(e, loading_window, app)

def _initialize_tray_ui(tray, loading_window, app):
    loading_window.set_status("Initializing application...")
    loading_window.set_progress(10)
    app.processEvents()
    tray.initialize()

def _initialize_recorder(tray, loading_window, app):
    loading_window.set_status("Initializing audio system...")
    loading_window.set_progress(25)
    app.processEvents()
    tray.recorder = AudioRecorder()

def _initialize_transcriber(tray, loading_window, app):
    settings = Settings()
    model_name = settings.get('model', DEFAULT_WHISPER_MODEL)
    
    # Check if model is downloaded
    model_name = _verify_model_availability(model_name, settings, loading_window, app)
    
    loading_window.set_status(f"Loading Whisper model: {model_name}")
    loading_window.set_progress(50)
    app.processEvents()
    
    try:
        tray.transcriber = WhisperTranscriber()
        loading_window.set_progress(80)
        app.processEvents()
    except Exception as e:
        _handle_transcriber_initialization_error(e, loading_window, app)
        # Create transcriber anyway, it will handle errors during transcription
        tray.transcriber = WhisperTranscriber()

def _verify_model_availability(model_name, settings, loading_window, app):
    """Verify that the selected model is available, or fall back to default"""
    try:
        model_info, _ = get_model_info()
        if model_name in model_info and not model_info[model_name]['is_downloaded']:
            loading_window.set_status(f"Whisper model '{model_name}' is not downloaded. Using default model.")
            loading_window.set_progress(40)
            app.processEvents()
            # Set model to default if current model is not downloaded
            settings.set('model', DEFAULT_WHISPER_MODEL)
            return DEFAULT_WHISPER_MODEL
    except Exception as model_error:
        logger.error(f"Error checking model info: {model_error}")
        loading_window.set_status("Error checking model info. Using default model.")
        loading_window.set_progress(40)
        app.processEvents()
        # Set model to default if there was an error
        settings.set('model', DEFAULT_WHISPER_MODEL)
        return DEFAULT_WHISPER_MODEL
    
    return model_name

def _handle_transcriber_initialization_error(e, loading_window, app):
    logger.error(f"Failed to initialize transcriber: {e}")
    QMessageBox.critical(None, "Error",
        f"Failed to load Whisper model: {str(e)}\n\nPlease check Settings to download the model.")
    loading_window.set_progress(80)
    app.processEvents()

def _connect_signals(tray, loading_window, app):
    loading_window.set_status("Setting up signal handlers...")
    loading_window.set_progress(90)
    app.processEvents()
    
    # Connect recorder signals
    tray.recorder.volume_updated.connect(tray.update_volume_meter)
    tray.recorder.recording_finished.connect(tray.handle_recording_finished)
    tray.recorder.recording_error.connect(tray.handle_recording_error)
    
    # Connect transcriber signals
    tray.transcriber.transcription_progress.connect(tray.update_processing_status)
    tray.transcriber.transcription_progress_percent.connect(tray.update_processing_progress)
    tray.transcriber.transcription_finished.connect(tray.handle_transcription_finished)
    tray.transcriber.transcription_error.connect(tray.handle_transcription_error)

def _finalize_tray_initialization(tray, loading_window):
    loading_window.set_status("Starting application...")
    loading_window.set_progress(100)
    QApplication.instance().processEvents()
    
    # Make tray visible
    tray.setVisible(True)
    
    # Signal completion
    tray.initialization_complete.emit()

def _handle_initialization_error(e, loading_window, app):
    logger.error(f"Initialization failed: {e}")
    QMessageBox.critical(None, "Error", f"Failed to initialize application: {str(e)}")
    loading_window.close()
    # Ensure the application can be closed with CTRL+C
    app.quit()