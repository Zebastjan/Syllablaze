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
from blaze.backends.registry import ModelRegistry
from blaze.backends.backend_health import BackendHealthRegistry, BackendHealthStatus
from blaze.managers.coordinator_transcriber import CoordinatorTranscriber

logger = logging.getLogger(__name__)


class TranscriberFactory:
    """Factory for creating appropriate transcriber based on backend type.

    This factory centralizes the logic for creating transcribers, ensuring
    proper backend selection through the unified BackendCoordinator.
    """

    @staticmethod
    def create_transcriber(backend_type: str, settings):
        """Create a transcriber for the specified backend.

        All backends now use CoordinatorTranscriber which routes through
        BackendCoordinator for unified backend management.

        Args:
            backend_type: The backend type (e.g., 'whisper', 'granite', 'liquid')
            settings: Application settings instance

        Returns:
            BaseTranscriber: CoordinatorTranscriber instance
        """
        from blaze.managers.coordinator_transcriber import CoordinatorTranscriber

        logger.info(f"Creating transcriber for backend: {backend_type}")
        return CoordinatorTranscriber(settings)

    @staticmethod
    def get_backend_for_model(model_id: str) -> str:
        """Get the backend type for a given model ID.

        Args:
            model_id: The model ID to look up

        Returns:
            Backend type string (e.g., 'whisper', 'granite')
        """
        backend = ModelRegistry.get_backend_for_model(model_id)
        return backend if backend else "whisper"  # Default to whisper if unknown


class TranscriptionManager(QObject):
    """Manager class for transcription operations"""

    # Define signals
    transcription_progress = pyqtSignal(str)  # Signal for progress updates
    transcription_progress_percent = pyqtSignal(int)  # Signal for progress percentage
    transcription_finished = pyqtSignal(str)  # Signal for completed transcription
    transcription_error = pyqtSignal(str)  # Signal for transcription errors
    model_changed = pyqtSignal(str)  # Signal for model changes
    language_changed = pyqtSignal(str)  # Signal for language changes
    backend_error = pyqtSignal(
        str, str
    )  # Signal for backend errors (backend_name, error_message)

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
        self._health_registry = BackendHealthRegistry()

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

    def check_gpu_memory(self, required_gb=4.0):
        """Check if sufficient GPU memory is available

        Parameters:
        -----------
        required_gb : float
            Required GPU memory in GB (default 4.0)

        Returns:
        --------
        tuple
            (bool, str) - (has_enough_memory, message)
        """
        try:
            import torch

            if not torch.cuda.is_available():
                return True, "CPU mode - no GPU memory check needed"

            # Get current GPU memory stats
            device = torch.cuda.current_device()
            total_memory = torch.cuda.get_device_properties(device).total_memory / (
                1024**3
            )
            allocated_memory = torch.cuda.memory_allocated(device) / (1024**3)
            reserved_memory = torch.cuda.memory_reserved(device) / (1024**3)
            free_memory = total_memory - allocated_memory

            logger.info(
                f"GPU memory: {free_memory:.1f}GB free / {total_memory:.1f}GB total "
                f"(allocated: {allocated_memory:.1f}GB, reserved: {reserved_memory:.1f}GB)"
            )

            if free_memory < required_gb:
                return False, (
                    f"GPU memory insufficient: {free_memory:.1f}GB free, "
                    f"{required_gb:.1f}GB required. "
                    f"Close other GPU applications or use a smaller model."
                )

            return True, f"GPU memory OK: {free_memory:.1f}GB free"

        except ImportError:
            return True, "PyTorch not available - skipping GPU memory check"
        except Exception as e:
            logger.warning(f"Error checking GPU memory: {e}")
            return True, f"Could not check GPU memory: {e}"

    def _get_transcriber_type(self) -> str:
        """Get the type of the current transcriber.

        Returns:
        --------
        str
            'whisper', 'coordinator', 'dummy', or 'unknown'
        """
        if self.transcriber is None:
            return "unknown"

        # Check for dummy transcriber first (has marker attribute)
        if hasattr(self.transcriber, "_is_dummy_transcriber"):
            return "dummy"

        # Use type checking - wrap in try/except to handle mocked classes in tests
        # and import errors from misconfigured backends
        try:
            from blaze.managers.coordinator_transcriber import CoordinatorTranscriber

            if isinstance(self.transcriber, CoordinatorTranscriber):
                return "coordinator"
        except (TypeError, ImportError, Exception) as e:
            # Handle case where classes are mocked in tests or imports fail
            logger.debug(f"Error determining transcriber type: {e}")
            pass

        # Fallback: check by class name
        class_name = self.transcriber.__class__.__name__
        if class_name == "CoordinatorTranscriber":
            return "coordinator"
        elif class_name == "DummyTranscriber":
            return "dummy"

        return "unknown"

    def initialize(self):
        """Initialize the transcriber with eager model loading.

        This method creates the appropriate transcriber and immediately loads
        the model so it's ready for transcription when the user presses the shortcut.

        Returns:
        --------
        bool
            True if initialization was successful (model is loaded and ready), False otherwise
        """
        # Get model name from settings
        model_name = self.settings.get("model", DEFAULT_WHISPER_MODEL)

        # ALWAYS derive backend from model_id - never use stored model_backend
        backend_type = ModelRegistry.get_backend_for_model(model_name) or "whisper"

        try:
            # Configure optimal settings
            self.configure_optimal_settings()

            logger.info(
                f"Initializing transcriber for model: {model_name} (backend: {backend_type})"
            )

            # Check GPU memory before loading model (especially important for large models)
            memory_ok, memory_msg = self.check_gpu_memory(required_gb=4.0)
            if not memory_ok:
                logger.error(f"GPU memory check failed: {memory_msg}")
                self.transcription_error.emit(f"Cannot load model: {memory_msg}")
                raise RuntimeError(memory_msg)
            else:
                logger.info(memory_msg)

            # Use factory to create appropriate transcriber for the backend
            self.transcriber = TranscriberFactory.create_transcriber(
                backend_type, self.settings
            )
            logger.info(f"Created transcriber for {backend_type} backend using factory")

            # Connect signals
            self.transcriber.transcription_progress.connect(self.transcription_progress)
            self.transcriber.transcription_progress_percent.connect(
                self.transcription_progress_percent
            )
            self.transcriber.transcription_finished.connect(self.transcription_finished)
            self.transcriber.transcription_error.connect(self.transcription_error)
            self.transcriber.model_changed.connect(self.model_changed)
            self.transcriber.language_changed.connect(self.language_changed)

            # EAGER LOADING: Load the model immediately so it's ready for transcription
            logger.info(f"Eagerly loading model: {model_name}")
            if hasattr(self.transcriber, "load_model"):
                self.transcriber.load_model()

            # Verify model is actually loaded
            if not self.transcriber.is_model_loaded():
                raise RuntimeError(f"Model {model_name} failed to load properly")

            logger.info(
                f"Model {model_name} loaded successfully and ready for transcription"
            )

            # Store current model and language
            self.current_model = model_name
            self.current_language = self.settings.get("language", "auto")

            # Update backend health status
            self._health_registry.update_status(
                backend_type, BackendHealthStatus.HEALTHY
            )

            logger.info(
                f"Transcription manager initialized with model: {self.current_model}, language: {self.current_language}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize transcription manager: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            # Update backend health status
            self._health_registry.update_status(
                backend_type, BackendHealthStatus.FAILED, str(e)
            )

            # Emit backend error signal for UI notification
            error_msg = (
                f"{backend_type.capitalize()} backend failed to initialize: {str(e)}"
            )
            self.backend_error.emit(backend_type, error_msg)

            # DO NOT auto-fallback. Instead, create dummy transcriber and return False.
            # The user will see an error and can select a different model.
            self._create_dummy_transcriber(backend_type, str(e))

            # Don't raise - allow app to continue without a model
            # UI will show warnings and user can install backends via Settings
            return False

    def _create_dummy_transcriber(self, failed_backend: str, error_message: str):
        """Create a dummy transcriber when initialization fails.

        This dummy transcriber provides clear error messages to the user
        when a backend fails, without auto-fallback to another backend.

        Parameters:
        -----------
        failed_backend : str
            The name of the backend that failed (e.g., 'liquid', 'granite')
        error_message : str
            The error message from the failed initialization
        """

        class DummyTranscriber(QObject):
            """Dummy transcriber that shows clear error messages."""

            # Define signals at the class level
            transcription_progress = pyqtSignal(str)
            transcription_progress_percent = pyqtSignal(int)
            transcription_finished = pyqtSignal(str)
            transcription_error = pyqtSignal(str)
            model_changed = pyqtSignal(str)
            language_changed = pyqtSignal(str)

            def __init__(self, failed_backend: str, error_message: str):
                super().__init__()
                self._is_dummy_transcriber = True
                self.failed_backend = failed_backend
                self.error_message = error_message
                self._dummy_model = None  # Use different name to avoid detection issues

            def transcribe_audio(self, *args, **kwargs):
                error_msg = (
                    f"The {self.failed_backend.capitalize()} model could not be loaded. "
                    f"Please open Settings and select a different model.\n\n"
                    f"Error: {self.error_message}"
                )
                self.transcription_error.emit(error_msg)

            def transcribe(self, *args, **kwargs):
                error_msg = (
                    f"The {self.failed_backend.capitalize()} model could not be loaded. "
                    f"Please open Settings and select a different model.\n\n"
                    f"Error: {self.error_message}"
                )
                self.transcription_error.emit(error_msg)

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

            def cleanup(self):
                """Dummy cleanup - nothing to clean up"""
                pass

            @property
            def worker(self):
                """Dummy worker property - returns None"""
                return None

            @property
            def model(self):
                """Dummy model property - returns None"""
                return None

            @model.setter
            def model(self, value):
                """Dummy model setter - does nothing"""
                pass

        # Create the dummy transcriber with error context
        self.transcriber = DummyTranscriber(failed_backend, error_message)

        # Connect signals
        self.transcriber.transcription_progress.connect(self.transcription_progress)
        self.transcriber.transcription_progress_percent.connect(
            self.transcription_progress_percent
        )
        self.transcriber.transcription_finished.connect(self.transcription_finished)
        self.transcriber.transcription_error.connect(self.transcription_error)

        logger.warning(
            f"Created dummy transcriber for failed {failed_backend} backend: {error_message}"
        )

    def _check_backend_change(self):
        """Check if backend type has changed and reinitialize if needed.

        Unlike the old implementation, this ALWAYS derives the backend from
        the model_id in settings, never from a stored model_backend value.

        This method includes comprehensive error recovery - if reinitialization
        fails, it keeps the current state (or dummy transcriber) and returns False
        rather than crashing.

        Returns:
        --------
        bool
            True if transcriber is correct type (or was reinitialized), False otherwise
        """
        try:
            # Get current model from settings
            current_model = self.settings.get("model", DEFAULT_WHISPER_MODEL)
            logger.info(
                f"[CHECK_BACKEND_CHANGE] Current model from settings: {current_model}"
            )

            # ALWAYS derive backend from model_id
            expected_backend = (
                ModelRegistry.get_backend_for_model(current_model) or "whisper"
            )
            logger.info(
                f"[CHECK_BACKEND_CHANGE] Expected backend for {current_model}: {expected_backend}"
            )

            # Get current transcriber type using proper type checking
            current_type = self._get_transcriber_type()
            logger.info(
                f"[CHECK_BACKEND_CHANGE] Current transcriber type: {current_type}"
            )

            # Map expected backend to transcriber type
            expected_type = (
                "whisper" if expected_backend == "whisper" else "coordinator"
            )
            logger.info(
                f"[CHECK_BACKEND_CHANGE] Expected transcriber type: {expected_type}"
            )

            # Check if reinitialization is needed
            if current_type != expected_type:
                logger.info(
                    f"Backend mismatch detected: have {current_type}, need {expected_type} "
                    f"for model {current_model} (backend: {expected_backend})"
                )

                # Check if this backend has failed recently
                if self._health_registry.is_failed(expected_backend):
                    last_error = self._health_registry.get_last_error(expected_backend)
                    logger.warning(
                        f"Backend {expected_backend} has failed before: {last_error}"
                    )
                    # Still try to reinitialize - user may have fixed the issue

                # Store old transcriber type for rollback on failure
                old_transcriber_type = current_type

                try:
                    # Clean up current transcriber
                    logger.info("Cleaning up old transcriber...")
                    cleanup_success = self.cleanup()
                    if not cleanup_success:
                        logger.warning("Cleanup returned False, but continuing...")

                    # CRITICAL: Force aggressive GPU memory cleanup between different backends
                    # This prevents GPU memory corruption when switching (e.g., Whisper -> Liquid)
                    logger.info("Forcing GPU memory cleanup between backend switch...")
                    self._force_gpu_memory_cleanup()

                    # Small delay to ensure GPU operations are fully complete
                    import time

                    time.sleep(0.5)

                    # Reinitialize with new backend
                    logger.info(f"Reinitializing for backend: {expected_backend}")
                    result = self.initialize()

                    if not result:
                        logger.error(
                            f"Failed to reinitialize for backend {expected_backend}"
                        )
                        # Backend initialization failed - we now have a dummy transcriber
                        # or possibly None. This is expected behavior - don't crash.
                        return False

                    logger.info(
                        f"Successfully reinitialized for backend {expected_backend}"
                    )
                    return True

                except Exception as e:
                    logger.error(f"Error during backend switch: {e}")
                    logger.debug(traceback.format_exc())

                    # Attempt to restore old state if possible
                    if (
                        old_transcriber_type != "unknown"
                        and old_transcriber_type != "dummy"
                    ):
                        logger.warning(
                            f"Attempting to restore old {old_transcriber_type} transcriber..."
                        )
                        try:
                            # Try to reinitialize with the old backend
                            old_model = self.settings.get(
                                "model", DEFAULT_WHISPER_MODEL
                            )
                            self.initialize()
                            logger.info("Restored previous transcriber")
                        except Exception as restore_error:
                            logger.error(
                                f"Failed to restore old transcriber: {restore_error}"
                            )

                    return False

            # Types match, but check if model changed within coordinator transcriber
            # For coordinator transcribers (Liquid, Qwen, Granite), we need to check
            # if the specific model changed, not just the transcriber type
            if current_type == "coordinator" and isinstance(
                self.transcriber, CoordinatorTranscriber
            ):
                # Check if the coordinator has the correct model loaded
                coordinator_model = getattr(
                    self.transcriber, "_current_model_name", None
                )
                logger.info(
                    f"[CHECK_BACKEND_CHANGE] Coordinator model check: "
                    f"loaded={coordinator_model}, expected={current_model}"
                )

                if coordinator_model != current_model:
                    # Model changed within coordinator - need to reload
                    logger.info(
                        f"[CHECK_BACKEND_CHANGE] Model mismatch in coordinator: "
                        f"have {coordinator_model}, need {current_model}. Triggering reload."
                    )
                    # Just return True - the transcriber will lazy-load on next transcription
                    # But we should eagerly load here to match user expectations
                    try:
                        # Tell coordinator to load the new model
                        self._transcriber.load_model_with_fallback(current_model)
                        logger.info(
                            f"[CHECK_BACKEND_CHANGE] Successfully loaded {current_model} in coordinator"
                        )
                    except Exception as e:
                        logger.error(
                            f"[CHECK_BACKEND_CHANGE] Failed to load {current_model}: {e}"
                        )
                        # Don't fail - let it lazy-load on transcription
                    return True

            # No change needed - current backend and model are correct
            logger.info(
                f"[CHECK_BACKEND_CHANGE] No change needed - backend and model are correct"
            )
            return True

        except Exception as e:
            logger.error(f"Critical error in _check_backend_change: {e}")
            logger.debug(traceback.format_exc())
            return False

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
            # Don't emit generic error - the initialize() already emitted a specific one
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

            # Check if backend changed
            old_backend = (
                ModelRegistry.get_backend_for_model(self.current_model) or "whisper"
            )
            new_backend = ModelRegistry.get_backend_for_model(model_name) or "whisper"

            if old_backend != new_backend:
                logger.info(f"Backend change detected: {old_backend} -> {new_backend}")
                # Full reinitialization needed
                self.cleanup()
                return self.initialize()

            # Same backend, just update the model
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

        transcriber_type = self._get_transcriber_type()

        if transcriber_type == "dummy":
            # Get the failed backend info
            if hasattr(self.transcriber, "failed_backend"):
                backend = self.transcriber.failed_backend
                return f"{backend.capitalize()} backend failed. Please select a different model in Settings."
            return "Model initialization failed. Please select a different model."

        if not self.transcriber.is_model_loaded():
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

        transcriber_type = self._get_transcriber_type()
        if transcriber_type == "dummy":
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

        transcriber_type = self._get_transcriber_type()
        if transcriber_type == "dummy":
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
            transcriber_type = self._get_transcriber_type()
            if transcriber_type == "dummy":
                return

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

    def _force_gpu_memory_cleanup(self):
        """Force aggressive GPU memory cleanup between backend switches.

        This is critical when switching between different backends (e.g., Whisper -> Liquid)
        to prevent GPU memory corruption and crashes.
        """
        logger.info("Forcing aggressive GPU memory cleanup...")

        try:
            import torch

            if torch.cuda.is_available():
                # Synchronize all CUDA operations first
                torch.cuda.synchronize()

                # Empty cache multiple times with sync in between
                for i in range(3):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()

                # Reset peak memory stats
                for device_id in range(torch.cuda.device_count()):
                    torch.cuda.reset_peak_memory_stats(device_id)

                logger.info("GPU memory cleanup completed")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error during GPU memory cleanup: {e}")

    def _disconnect_transcriber_signals(self):
        """Disconnect all signals from the current transcriber.

        This must be called before cleanup to prevent callbacks on stale objects.
        """
        if not self.transcriber:
            return

        try:
            logger.debug("Disconnecting transcriber signals...")
            signals = [
                "transcription_progress",
                "transcription_progress_percent",
                "transcription_finished",
                "transcription_error",
                "model_changed",
                "language_changed",
            ]
            for signal_name in signals:
                if hasattr(self.transcriber, signal_name):
                    try:
                        signal = getattr(self.transcriber, signal_name)
                        signal.disconnect()
                        logger.debug(f"Disconnected signal: {signal_name}")
                    except (TypeError, RuntimeError):
                        # Signal was not connected or already disconnected
                        pass
                    except Exception as e:
                        logger.debug(f"Error disconnecting {signal_name}: {e}")
        except Exception as e:
            logger.warning(f"Error during signal disconnection: {e}")

    def cleanup(self):
        """Clean up transcription resources safely.

        This method ensures proper cleanup even if the transcriber is in a
        bad state. It disconnects signals first to prevent callbacks during
        cleanup, then releases resources.

        Returns:
        --------
        bool
            True if cleanup was successful, False otherwise
        """
        if not self.transcriber:
            return True

        transcriber_ref = self.transcriber
        cleanup_errors = []

        try:
            logger.info("Starting transcription manager cleanup...")

            # CRITICAL: Disconnect signals first to prevent callbacks during cleanup
            self._disconnect_transcriber_signals()

            # Check if this is an isolated backend (subprocess)
            if hasattr(transcriber_ref, "stop"):
                logger.info("Stopping isolated backend subprocess...")
                try:
                    transcriber_ref.stop()
                    logger.info("Isolated backend stopped successfully")
                except Exception as e:
                    logger.warning(f"Error stopping isolated backend: {e}")
                    cleanup_errors.append(f"isolated_stop: {e}")
                finally:
                    # Always clear reference even if stop() failed
                    self.transcriber = None
                    gc.collect()
                    self._force_gpu_memory_cleanup()
                return True

            transcriber_type = self._get_transcriber_type()

            # For dummy transcribers, just clear the reference
            if transcriber_type == "dummy":
                logger.info("Cleaning up dummy transcriber")
                self.transcriber = None
                gc.collect()
                return True

            # Call transcriber's cleanup() method (CRITICAL: fixes broken cleanup chain)
            if hasattr(transcriber_ref, "cleanup"):
                logger.info("Calling transcriber cleanup...")
                try:
                    transcriber_ref.cleanup()
                    logger.info("Transcriber cleanup completed")
                except Exception as e:
                    logger.warning(f"Error during transcriber cleanup: {e}")
                    cleanup_errors.append(f"cleanup: {e}")

            # Use cancel_transcription for worker shutdown (reuses three-phase pattern)
            if hasattr(transcriber_ref, "worker") and transcriber_ref.worker:
                try:
                    if transcriber_ref.worker.isRunning():
                        logger.info("Waiting for transcription worker to finish...")
                        self.cancel_transcription(timeout_ms=4000)
                except Exception as e:
                    logger.warning(f"Error stopping worker: {e}")
                    cleanup_errors.append(f"worker: {e}")

            # Additional cleanup for Whisper backend
            if transcriber_type == "whisper":
                if (
                    hasattr(transcriber_ref, "model")
                    and transcriber_ref.model is not None
                ):
                    logger.info("Releasing Whisper model resources")
                    try:
                        transcriber_ref.model = None
                    except Exception as e:
                        logger.warning(f"Error releasing model: {e}")
                        cleanup_errors.append(f"model: {e}")

            # Always clear the reference
            self.transcriber = None
            gc.collect()

            # Use aggressive GPU memory cleanup
            self._force_gpu_memory_cleanup()

            if cleanup_errors:
                logger.warning(
                    f"Cleanup completed with {len(cleanup_errors)} errors: {cleanup_errors}"
                )
            else:
                logger.info("Transcription manager cleaned up successfully")

            return True

        except Exception as e:
            logger.error(f"Critical error during cleanup: {e}")
            logger.debug(traceback.format_exc())
            # Still try to clear the reference
            try:
                self.transcriber = None
                gc.collect()
            except Exception:
                pass
            return False

    def get_backend_health(self) -> dict:
        """Get health status for all backends.

        Returns:
        --------
        dict
            Dictionary mapping backend names to their health status
        """
        health_data = self._health_registry.get_all_health()
        return {
            name: {
                "status": health.status.value,
                "last_error": health.last_error,
                "consecutive_failures": health.consecutive_failures,
            }
            for name, health in health_data.items()
        }
