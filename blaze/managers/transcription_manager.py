"""
Transcription Manager for Syllablaze

This module provides a centralized manager for transcription operations,
reducing code duplication and improving maintainability.
"""

import logging
import gc
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
from blaze.constants import (
    DEFAULT_WHISPER_MODEL,
    DEFAULT_BEAM_SIZE,
    DEFAULT_VAD_FILTER,
    DEFAULT_WORD_TIMESTAMPS,
)

logger = logging.getLogger(__name__)


class TranscriptionManager(QObject):
    """Manager class for transcription operations"""

    # Define signals
    transcription_progress = pyqtSignal(str)  # Signal for progress updates
    transcription_progress_percent = pyqtSignal(int)  # Signal for progress percentage
    transcription_finished = pyqtSignal(str)  # Signal for completed transcription
    transcription_error = pyqtSignal(str)  # Signal for transcription errors
    model_changed = pyqtSignal(str)  # Signal for model changes
    language_changed = pyqtSignal(str)  # Signal for language changes

    def __init__(self, settings):
        """Initialize the transcription manager

        Parameters:
        -----------
        settings : Settings
            Application settings
        """
        super().__init__()
        self.settings = settings
        self.transcriber = None
        self.current_model = None
        self.current_language = None

    def configure_optimal_settings(self):
        """Configure optimal settings for Faster Whisper

        Sets default values for transcription parameters if not already configured.
        Device and compute_type should already be configured by GPUSetupManager.

        Returns:
        --------
        bool
            True if configuration was successful, False otherwise
        """
        try:
            # Set transcription defaults if this is the first run
            if self.settings.get("beam_size") is None:
                self.settings.set("beam_size", DEFAULT_BEAM_SIZE)
            if self.settings.get("vad_filter") is None:
                self.settings.set("vad_filter", DEFAULT_VAD_FILTER)
            if self.settings.get("word_timestamps") is None:
                self.settings.set("word_timestamps", DEFAULT_WORD_TIMESTAMPS)

            logger.info("Transcription settings configured with optimal defaults.")

            return True
        except Exception as e:
            logger.error(f"Failed to configure optimal settings: {e}")
            return False

    def initialize(self):
        """Initialize the transcriber

        Returns:
        --------
        bool
            True if initialization was successful, False otherwise
        """
        # Get settings first so they're available in exception handler
        model_name = self.settings.get("model", DEFAULT_WHISPER_MODEL)
        backend_type = self.settings.get("model_backend", "whisper")

        try:
            # Configure optimal settings
            self.configure_optimal_settings()

            logger.info(
                f"Initializing transcriber for model: {model_name} (backend: {backend_type})"
            )

            if backend_type == "whisper":
                # Use WhisperTranscriber for Whisper models
                from blaze.transcriber import WhisperTranscriber

                self.transcriber = WhisperTranscriber()
                logger.info("Using WhisperTranscriber for Whisper backend")
            else:
                # Use CoordinatorTranscriber for other backends (Granite, Liquid, Qwen)
                from blaze.managers.coordinator_transcriber import (
                    CoordinatorTranscriber,
                )

                self.transcriber = CoordinatorTranscriber(self.settings)
                logger.info(f"Using CoordinatorTranscriber for {backend_type} backend")

            # Connect signals
            self.transcriber.transcription_progress.connect(self.transcription_progress)
            self.transcriber.transcription_progress_percent.connect(
                self.transcription_progress_percent
            )
            self.transcriber.transcription_finished.connect(self.transcription_finished)
            self.transcriber.transcription_error.connect(self.transcription_error)
            self.transcriber.model_changed.connect(self.model_changed)
            self.transcriber.language_changed.connect(self.language_changed)

            # Store current model and language
            self.current_model = model_name
            self.current_language = self.settings.get("language", "auto")

            logger.info(
                f"Transcription manager initialized with model: {self.current_model}, language: {self.current_language}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize transcription manager: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            # Try fallback to Whisper if configured backend failed
            if backend_type != "whisper":
                logger.info("Attempting fallback to Whisper backend...")
                try:
                    from blaze.transcriber import WhisperTranscriber

                    self.transcriber = WhisperTranscriber()
                    logger.info("Successfully fell back to WhisperTranscriber")

                    # Connect signals
                    self.transcriber.transcription_progress.connect(
                        self.transcription_progress
                    )
                    self.transcriber.transcription_progress_percent.connect(
                        self.transcription_progress_percent
                    )
                    self.transcriber.transcription_finished.connect(
                        self.transcription_finished
                    )
                    self.transcriber.transcription_error.connect(
                        self.transcription_error
                    )
                    self.transcriber.model_changed.connect(self.model_changed)
                    self.transcriber.language_changed.connect(self.language_changed)

                    # Store current model and language
                    self.current_model = model_name
                    self.current_language = self.settings.get("language", "auto")

                    logger.warning(
                        f"Using fallback Whisper backend. Original {backend_type} backend failed."
                    )
                    return True
                except Exception as fallback_e:
                    logger.error(f"Fallback to Whisper also failed: {fallback_e}")

            self._create_dummy_transcriber()
            return False

    def _create_dummy_transcriber(self):
        """Create a dummy transcriber when initialization fails"""

        # Create a dummy transcriber that will show a message when used
        class DummyTranscriber(QObject):
            # Define signals at the class level
            transcription_progress = pyqtSignal(str)
            transcription_progress_percent = pyqtSignal(int)
            transcription_finished = pyqtSignal(str)
            transcription_error = pyqtSignal(str)
            model_changed = pyqtSignal(str)
            language_changed = pyqtSignal(str)

            def __init__(self):
                super().__init__()  # Initialize the QObject base class
                self.model = None
                self.current_model_name = (
                    None  # For CoordinatorTranscriber compatibility
                )

            def transcribe_audio(self, *args, **kwargs):
                self.transcription_error.emit(
                    "Transcription failed: Model initialization error. Please check Settings and ensure a model is selected and downloaded."
                )

            def transcribe(self, *args, **kwargs):
                self.transcription_error.emit(
                    "Transcription failed: Model initialization error. Please check Settings and ensure a model is selected and downloaded."
                )

            def update_model(self, *args, **kwargs):
                return False

            def update_language(self, *args, **kwargs):
                return False

            def is_model_loaded(self):
                """Dummy transcriber never has a model loaded"""
                return False

            def reload_model_if_needed(self):
                """Dummy transcriber cannot reload"""
                return False

        # Create a dummy transcriber with the same interface
        self.transcriber = DummyTranscriber()

        # Connect signals
        self.transcriber.transcription_progress.connect(self.transcription_progress)
        self.transcriber.transcription_progress_percent.connect(
            self.transcription_progress_percent
        )
        self.transcriber.transcription_finished.connect(self.transcription_finished)
        self.transcriber.transcription_error.connect(self.transcription_error)

        logger.warning("Created dummy transcriber due to initialization failure")

    def _check_backend_change(self):
        """Check if backend type has changed and reinitialize if needed"""
        current_backend = self.settings.get("model_backend", "whisper")

        # Determine what type of transcriber we currently have
        current_transcriber_type = None
        if hasattr(self.transcriber, "model"):
            current_transcriber_type = "whisper"
        elif hasattr(self.transcriber, "current_model_name"):
            current_transcriber_type = "coordinator"

        # If backend type doesn't match, reinitialize
        if current_backend == "whisper" and current_transcriber_type != "whisper":
            logger.info(f"Backend changed to whisper, reinitializing transcriber")
            self.cleanup()
            return self.initialize()
        elif current_backend != "whisper" and current_transcriber_type != "coordinator":
            logger.info(
                f"Backend changed to {current_backend}, reinitializing transcriber"
            )
            self.cleanup()
            return self.initialize()

        return True

    def transcribe_audio(self, audio_data):
        """Transcribe audio data

        Parameters:
        -----------
        audio_data : numpy.ndarray
            Audio data to transcribe

        Returns:
        --------
        bool
            True if transcription started successfully, False otherwise
        """
        if not self.transcriber:
            logger.error("Cannot transcribe: transcriber not initialized")
            self.transcription_error.emit("Transcriber not initialized")
            return False

        # Check if backend type has changed and reinitialize if needed
        if not self._check_backend_change():
            logger.error("Failed to reinitialize transcriber for backend change")
            self.transcription_error.emit("Failed to switch transcription backend")
            return False

        try:
            self.transcriber.transcribe_audio(audio_data)
            return True
        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            self.transcription_error.emit(f"Failed to start transcription: {str(e)}")
            return False

    def update_model(self, model_name=None):
        """Update the transcription model

        Parameters:
        -----------
        model_name : str
            Name of the model to use (optional)

        Returns:
        --------
        bool
            True if model was updated, False otherwise
        """
        if not self.transcriber:
            logger.error("Cannot update model: transcriber not initialized")
            return False

        try:
            # Get model name from settings if not provided
            if model_name is None:
                model_name = self.settings.get("model", DEFAULT_WHISPER_MODEL)

            # Update model
            result = self.transcriber.update_model(model_name)

            if result:
                self.current_model = model_name
                logger.info(f"Model updated to: {model_name}")

            return result
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
            return False

    def update_language(self, language=None):
        """Update the transcription language

        Parameters:
        -----------
        language : str
            Language code to use (optional)

        Returns:
        --------
        bool
            True if language was updated, False otherwise
        """
        if not self.transcriber:
            logger.error("Cannot update language: transcriber not initialized")
            return False

        try:
            # Get language from settings if not provided
            if language is None:
                language = self.settings.get("language", "auto")

            # Update language
            result = self.transcriber.update_language(language)

            if result:
                self.current_language = language
                logger.info(f"Language updated to: {language}")

            return result
        except Exception as e:
            logger.error(f"Failed to update language: {e}")
            return False

    def is_model_loaded(self):
        """Check if a model is loaded and ready for transcription

        Returns:
        --------
        bool
            True if model is loaded, False otherwise
        """
        if not self.transcriber:
            return False

        # Use the transcriber's is_model_loaded() method if available
        if hasattr(self.transcriber, "is_model_loaded"):
            try:
                return self.transcriber.is_model_loaded()
            except Exception as e:
                logger.warning(f"Error checking model loaded status: {e}")
                return False

        # Fallback: Check for WhisperTranscriber (has model attribute)
        if hasattr(self.transcriber, "model"):
            return self.transcriber.model is not None

        # Fallback: Check for CoordinatorTranscriber (has current_model_name attribute)
        if hasattr(self.transcriber, "current_model_name"):
            return self.transcriber.current_model_name is not None

        return False

    def get_model_status(self):
        """Get current model status as a human-readable string

        Returns:
        --------
        str
            Status message describing the model state
        """
        if not self.transcriber:
            return "Transcriber not initialized"

        if not hasattr(self.transcriber, "model"):
            return "Transcriber not properly configured"

        if self.transcriber.model is None:
            return "No model loaded. Please download a model in Settings."

        model_name = self.current_model or "unknown"
        return f"Model loaded: {model_name}"

    def is_worker_running(self):
        """Check if transcription worker thread is actually running

        This catches race conditions where the ApplicationState flag
        is cleared but the worker thread is still executing CTranslate2
        inference (common under high system load).

        Returns:
        --------
        bool
            True if worker thread exists and is running
        """
        if not self.transcriber:
            return False
        if not hasattr(self.transcriber, "worker") or not self.transcriber.worker:
            return False
        return self.transcriber.worker.isRunning()

    def cancel_transcription(self, timeout_ms=5000):
        """Cancel in-progress transcription with graceful resource cleanup

        Uses three-phase shutdown pattern (same as cleanup()) to ensure
        CTranslate2 semaphores are properly released even if thread is
        blocked in a C++ call.

        Parameters:
        -----------
        timeout_ms : int
            Total timeout in milliseconds (default 5000)

        Returns:
        --------
        bool
            True if cancellation successful, False otherwise
        """
        if not self.transcriber:
            return True

        if not hasattr(self.transcriber, "worker") or not self.transcriber.worker:
            return True

        worker = self.transcriber.worker
        if not worker.isRunning():
            logger.debug("Worker not running, nothing to cancel")
            return True

        try:
            logger.info("Cancelling in-progress transcription...")

            # Phase 1: Graceful quit (60% of timeout)
            graceful_timeout = int(timeout_ms * 0.6)
            worker.quit()
            if worker.wait(graceful_timeout):
                logger.info("Worker stopped gracefully")
                self._cleanup_worker_resources()
                return True

            # Phase 2: Force terminate (40% of timeout)
            logger.warning("Worker did not stop gracefully; forcefully terminating")
            worker.terminate()
            forced_timeout = int(timeout_ms * 0.4)
            worker.wait(forced_timeout)

            self._cleanup_worker_resources()
            logger.info("Worker terminated and resources cleaned up")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel transcription: {e}")
            logger.debug(traceback.format_exc())
            return False

    def _cleanup_worker_resources(self):
        """Clean up CTranslate2 model resources after worker termination

        Releases model reference, collects garbage, and clears CUDA cache
        to ensure CTranslate2's internal semaphores are properly released.
        """
        try:
            if (
                hasattr(self.transcriber, "model")
                and self.transcriber.model is not None
            ):
                logger.debug("Releasing model reference after worker termination")
                self.transcriber.model = None

            gc.collect()

            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    logger.debug("Cleared CUDA cache after worker termination")
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Error clearing CUDA cache: {e}")

        except Exception as e:
            logger.warning(f"Error cleaning up worker resources: {e}")

    def cleanup(self):
        """Clean up transcription resources

        Returns:
        --------
        bool
            True if cleanup was successful, False otherwise
        """
        if not self.transcriber:
            return True

        try:
            logger.info("Starting transcription manager cleanup...")

            # Use cancel_transcription for worker shutdown (reuses three-phase pattern)
            if hasattr(self.transcriber, "worker") and self.transcriber.worker:
                if self.transcriber.worker.isRunning():
                    logger.info("Waiting for transcription worker to finish...")
                    self.cancel_transcription(timeout_ms=4000)

            # Additional cleanup for application shutdown
            if (
                hasattr(self.transcriber, "model")
                and self.transcriber.model is not None
            ):
                logger.info("Releasing Whisper model resources")
                try:
                    self.transcriber.model = None
                except Exception as e:
                    logger.warning(f"Error releasing model: {e}")

                gc.collect()

                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                        logger.info("Cleared CUDA cache")
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Error clearing CUDA cache: {e}")

            self.transcriber = None

            gc.collect()

            logger.info("Transcription manager cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clean up transcription manager: {e}")
            logger.debug(traceback.format_exc())
            return False
