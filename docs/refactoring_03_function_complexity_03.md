# Function/Method Length and Complexity - Part 3/3

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