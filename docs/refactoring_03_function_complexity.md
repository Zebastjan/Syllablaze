# Function/Method Length and Complexity

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

def quit_application(self):
    import os
    try:
        # Cleanup recorder
        if self.recorder:
            try:
                self.recorder.cleanup()
            except Exception as rec_error:
                logger.error(f"Error cleaning up recorder: {rec_error}")
            self.recorder = None
        
        # Close all windows
        if hasattr(self, 'settings_window') and self.settings_window:
            try:
                if self.settings_window.isVisible():
                    self.settings_window.close()
            except Exception as win_error:
                logger.error(f"Error closing settings window: {win_error}")
            
        if hasattr(self, 'progress_window') and self.progress_window:
            try:
                if self.progress_window.isVisible():
                    self.progress_window.close()
            except Exception as win_error:
                logger.error(f"Error closing progress window: {win_error}")
            
        # Stop recording if active
        if self.recording:
            try:
                self.stop_recording()
            except Exception as rec_error:
                logger.error(f"Error stopping recording: {rec_error}")
        
        # Wait for any running threads to finish
        if hasattr(self, 'transcriber') and self.transcriber:
            try:
                if hasattr(self.transcriber, 'worker') and self.transcriber.worker:
                    if self.transcriber.worker.isRunning():
                        logger.info("Waiting for transcription worker to finish...")
                        self.transcriber.worker.wait(5000)  # Wait up to 5 seconds
            except Exception as thread_error:
                logger.error(f"Error waiting for transcription worker: {thread_error}")
        
        # Release lock file if it exists
        global LOCK_FILE
        if LOCK_FILE:
            try:
                import fcntl
                # Release the lock
                fcntl.flock(LOCK_FILE, fcntl.LOCK_UN)
                LOCK_FILE.close()
                # Remove the lock file
                if os.path.exists(LOCK_FILE_PATH):
                    os.remove(LOCK_FILE_PATH)
                LOCK_FILE = None
                logger.info("Released application lock file")
            except Exception as lock_error:
                logger.error(f"Error releasing lock file: {lock_error}")
        
        logger.info("Application shutdown complete, exiting...")
        
        # Explicitly quit the application
        QApplication.instance().quit()
            
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")
        # Force exit if there was an error
        # Remove forced exit on error
```

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
```

```python
# For quit_application
def quit_application(self):
    try:
        self._cleanup_recorder()
        self._close_windows()
        self._stop_active_recording()
        self._wait_for_threads()
        self._release_lock_file()
        
        logger.info("Application shutdown complete, exiting...")
        
        # Explicitly quit the application
        QApplication.instance().quit()
            
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")

def _cleanup_recorder(self):
    if self.recorder:
        try:
            self.recorder.cleanup()
        except Exception as rec_error:
            logger.error(f"Error cleaning up recorder: {rec_error}")
        self.recorder = None

def _close_windows(self):
    # Close settings window
    if hasattr(self, 'settings_window') and self.settings_window:
        try:
            if self.settings_window.isVisible():
                self.settings_window.close()
        except Exception as win_error:
            logger.error(f"Error closing settings window: {win_error}")
        
    # Close progress window
    if hasattr(self, 'progress_window') and self.progress_window:
        try:
            if self.progress_window.isVisible():
                self.progress_window.close()
        except Exception as win_error:
            logger.error(f"Error closing progress window: {win_error}")

def _stop_active_recording(self):
    if self.recording:
        try:
            self.stop_recording()
        except Exception as rec_error:
            logger.error(f"Error stopping recording: {rec_error}")

def _wait_for_threads(self):
    if hasattr(self, 'transcriber') and self.transcriber:
        try:
            if hasattr(self.transcriber, 'worker') and self.transcriber.worker:
                if self.transcriber.worker.isRunning():
                    logger.info("Waiting for transcription worker to finish...")
                    self.transcriber.worker.wait(5000)  # Wait up to 5 seconds
        except Exception as thread_error:
            logger.error(f"Error waiting for transcription worker: {thread_error}")

def _release_lock_file(self):
    import os
    global LOCK_FILE
    if LOCK_FILE:
        try:
            import fcntl
            # Release the lock
            fcntl.flock(LOCK_FILE, fcntl.LOCK_UN)
            LOCK_FILE.close()
            # Remove the lock file
            if os.path.exists(LOCK_FILE_PATH):
                os.remove(LOCK_FILE_PATH)
            LOCK_FILE = None
            logger.info("Released application lock file")
        except Exception as lock_error:
            logger.error(f"Error releasing lock file: {lock_error}")
```

## 6.2. Complex Error Handling in check_already_running()

**Issue:** The `check_already_running()` function in `main.py` has complex error handling with nested try-except blocks.

**Example:**
```python
def check_already_running():
    """Check if Syllablaze is already running using a file lock mechanism"""
    global LOCK_FILE
    
    # Create directory if it doesn't exist
    lock_dir = os.path.dirname(LOCK_FILE_PATH)
    if not os.path.exists(lock_dir):
        try:
            os.makedirs(lock_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create lock directory: {e}")
            # Fall back to process-based check if we can't create the lock directory
            return _check_already_running_by_process()
    
    try:
        # Try to create and lock the file
        import fcntl
        
        # Check if the lock file exists
        if os.path.exists(LOCK_FILE_PATH):
            try:
                # Try to open the existing lock file for reading and writing
                test_lock = open(LOCK_FILE_PATH, 'r+')
                try:
                    # Try to get a non-blocking exclusive lock
                    fcntl.flock(test_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    
                    # If we got here, the file wasn't locked
                    # Read the PID from the file
                    test_lock.seek(0)
                    pid = test_lock.read().strip()
                    
                    # Check if the process with this PID is still running
                    if pid and pid.isdigit():
                        try:
                            # If we can send signal 0 to the process, it exists
                            os.kill(int(pid), 0)
                            # This is strange - the file exists and the process exists,
                            # but the file wasn't locked. This could happen if the process
                            # crashed without cleaning up. Let's assume it's not running.
                            logger.warning(f"Found process {pid} but lock file wasn't locked. Assuming stale lock.")
                        except OSError:
                            # Process doesn't exist
                            logger.info(f"Removing stale lock file for PID {pid}")
                    
                    # Release the lock and close the file
                    fcntl.flock(test_lock, fcntl.LOCK_UN)
                    test_lock.close()
                    
                    # Remove the stale lock file
                    os.remove(LOCK_FILE_PATH)
                except IOError:
                    # The file is locked by another process
                    test_lock.close()
                    logger.info("Lock file is locked by another process")
                    return True
            except Exception as e:
                logger.error(f"Error checking existing lock file: {e}")
                # If we can't read the lock file, try to remove it
                try:
                    os.remove(LOCK_FILE_PATH)
                except:
                    pass
        
        # Create a new lock file
        LOCK_FILE = open(LOCK_FILE_PATH, 'w')
        # Write PID to the file
        LOCK_FILE.write(str(os.getpid()))
        LOCK_FILE.flush()
        # Log the lock file path for debugging
        logger.info(f"INFO: Lock file created at: {os.path.abspath(LOCK_FILE_PATH)}")
        
        try:
            # Try to get an exclusive lock
            fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.info(f"Acquired lock file for PID {os.getpid()}")
            return False
        except IOError:
            # This shouldn't happen since we just created the file,
            # but handle it just in case
            logger.error("Failed to acquire lock on newly created file")
            LOCK_FILE.close()
            LOCK_FILE = None
            return True
    except IOError as e:
        # Lock already held by another process
        logger.info(f"Lock already held by another process: {e}")
        if LOCK_FILE:
            LOCK_FILE.close()
            LOCK_FILE = None
        return True
    except Exception as e:
        logger.error(f"Error in file locking mechanism: {e}")
        # Fall back to process-based check if file locking fails
        if LOCK_FILE:
            LOCK_FILE.close()
            LOCK_FILE = None
        return _check_already_running_by_process()
```

**Solution:** Refactor into smaller, focused functions with clearer error handling:

```python
def check_already_running():
    """Check if Syllablaze is already running using a file lock mechanism"""
    global LOCK_FILE
    
    # Ensure lock directory exists
    if not _ensure_lock_directory_exists():
        return _check_already_running_by_process()
    
    # Check for and handle existing lock file
    if os.path.exists(LOCK_FILE_PATH):
        if _is_lock_file_locked():
            return True
    
    # Create and lock a new file
    return not _create_and_lock_new_file()

def _ensure_lock_directory_exists():
    """Ensure the lock directory exists"""
    lock_dir = os.path.dirname(LOCK_FILE_PATH)
    if not os.path.exists(lock_dir):
        try:
            os.makedirs(lock_dir, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create lock directory: {e}")
            return False
    return True

def _is_lock_file_locked():
    """Check if the existing lock file is locked by another process"""
    import fcntl
    
    try:
        # Try to open the existing lock file for reading and writing
        test_lock = open(LOCK_FILE_PATH, 'r+')
        try:
            # Try to get a non-blocking exclusive lock
            fcntl.flock(test_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # If we got here, the file wasn't locked
            # Check if the process is still running
            _check_and_handle_stale_lock(test_lock)
            
            # Release the lock and close the file
            fcntl.flock(test_lock, fcntl.LOCK_UN)
            test_lock.close()
            
            # Remove the stale lock file
            os.remove(LOCK_FILE_PATH)
            return False
        except IOError:
            # The file is locked by another process
            test_lock.close()
            logger.info("Lock file is locked by another process")
            return True
    except Exception as e:
        logger.error(f"Error checking existing lock file: {e}")
        # If we can't read the lock file, try to remove it
        try:
            os.remove(LOCK_FILE_PATH)
        except:
            pass
        return False

def _check_and_handle_stale_lock(test_lock):
    """Check if the process in the lock file is still running"""
    test_lock.seek(0)
    pid = test_lock.read().strip()
    
    if pid and pid.isdigit():
        try:
            # If we can send signal 0 to the process, it exists
            os.kill(int(pid), 0)
            # This is strange - the file exists and the process exists,
            # but the file wasn't locked. This could happen if the process
            # crashed without cleaning up. Let's assume it's not running.
            logger.warning(f"Found process {pid} but lock file wasn't locked. Assuming stale lock.")
        except OSError:
            # Process doesn't exist
            logger.info(f"Removing stale lock file for PID {pid}")

def _create_and_lock_new_file():
    """Create and lock a new lock file"""
    global LOCK_FILE
    import fcntl
    
    try:
        # Create a new lock file
        LOCK_FILE = open(LOCK_FILE_PATH, 'w')
        # Write PID to the file
        LOCK_FILE.write(str(os.getpid()))
        LOCK_FILE.flush()
        # Log the lock file path for debugging
        logger.info(f"INFO: Lock file created at: {os.path.abspath(LOCK_FILE_PATH)}")
        
        # Try to get an exclusive lock
        fcntl.flock(LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info(f"Acquired lock file for PID {os.getpid()}")
        return True
    except IOError:
        # This shouldn't happen since we just created the file
        logger.error("Failed to acquire lock on newly created file")
        if LOCK_FILE:
            LOCK_FILE.close()
            LOCK_FILE = None
        return False
    except Exception as e:
        logger.error(f"Error in file locking mechanism: {e}")
        if LOCK_FILE:
            LOCK_FILE.close()
            LOCK_FILE = None
        return False
```

## 6.3. Complex Callback Methods

**Issue:** Callback methods like `_callback` in `recorder.py` handle too many responsibilities.

**Example:**
```python
def _callback(self, in_data, frame_count, time_info, status):
    if status:
        logger.warning(f"Recording status: {status}")
    try:
        if self.is_recording:
            self.frames.append(in_data)
            # Calculate and emit volume level
            try:
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                if len(audio_data) > 0:
                    # Calculate RMS with protection against zero/negative values
                    squared = np.abs(audio_data)**2
                    mean_squared = np.mean(squared) if np.any(squared) else 0
                    rms = np.sqrt(mean_squared) if mean_squared > 0 else 0
                    # Normalize to 0-1 range
                    volume = min(1.0, max(0.0, rms / 32768.0))
                else:
                    volume = 0.0
                self.volume_updated.emit(volume)
            except Exception as e:
                logger.warning(f"Error calculating volume: {e}")
                self.volume_updated.emit(0.0)
            return (in_data, pyaudio.paContinue)
    except RuntimeError:
        # Handle case where object is being deleted
        logger.warning("AudioRecorder object is being cleaned up")
        return (in_data, pyaudio.paComplete)
    return (in_data, pyaudio.paComplete)
```

**Solution:** Split into smaller, focused methods:

```python
def _callback(self, in_data, frame_count, time_info, status):
    """Main callback for audio recording"""
    if status:
        logger.warning(f"Recording status: {status}")
    
    try:
        if self.is_recording:
            self._process_audio_frame(in_data)
            return (in_data, pyaudio.paContinue)
    except RuntimeError:
        # Handle case where object is being deleted
        logger.warning("AudioRecorder object is being cleaned up")
        return (in_data, pyaudio.paComplete)
    
    return (in_data, pyaudio.paComplete)

def _process_audio_frame(self, in_data):
    """Process a single frame of audio data"""
    # Store the frame
    self.frames.append(in_data)
    
    # Calculate and emit volume level
    volume = self._calculate_volume(in_data)
    self.volume_updated.emit(volume)

def _calculate_volume(self, in_data):
    """Calculate volume level from audio data"""
    try:
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        if len(audio_data) > 0:
            # Calculate RMS with protection against zero/negative values
            squared = np.abs(audio_data)**2
            mean_squared = np.mean(squared) if np.any(squared) else 0
            rms = np.sqrt(mean_squared) if mean_squared > 0 else 0
            # Normalize to 0-1 range
            return min(1.0, max(0.0, rms / 32768.0))
        else:
            return 0.0
    except Exception as e:
        logger.warning(f"Error calculating volume: {e}")
        return 0.0
```

This refactoring improves readability and testability by separating the different concerns of the callback method.