"""
Coordinator-based Transcriber for Multi-Backend Support

This module provides a transcriber that uses BackendCoordinator to support
multiple STT backends (Whisper, Granite, Liquid, Qwen) with a unified interface
that matches WhisperTranscriber's API.

This allows TranscriptionManager to route to the appropriate backend based
on the active model's backend type.
"""

import logging
import gc
import numpy as np
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from blaze.backends.coordinator import get_coordinator, BackendCoordinator
from blaze.backends.base import TranscriptionResult
from blaze.transcriber_base import BaseTranscriber

logger = logging.getLogger(__name__)


class CoordinatorTranscriptionWorker(QThread):
    """
    Worker thread for coordinator-based transcription.

    Runs transcription in a separate thread to avoid blocking the UI.
    """

    # Signals
    progress = pyqtSignal(str)  # Progress message
    progress_percent = pyqtSignal(int)  # Progress percentage (0-100)
    finished = pyqtSignal(str)  # Transcribed text
    error = pyqtSignal(str)  # Error message

    def __init__(
        self,
        coordinator: BackendCoordinator,
        audio_data: np.ndarray,
        language: Optional[str] = None,
    ):
        super().__init__()
        self.coordinator = coordinator
        self.audio_data = audio_data
        self.language = language
        self._is_running = False

    def run(self):
        """Run transcription in background thread"""
        self._is_running = True

        try:
            self.progress.emit("Processing audio...")
            self.progress_percent.emit(10)

            # Convert numpy array to bytes (16kHz PCM, int16)
            # Ensure the data is in the right format
            if self.audio_data.dtype != np.int16:
                # Convert float32 [-1.0, 1.0] to int16
                audio_int16 = (self.audio_data * 32767).astype(np.int16)
            else:
                audio_int16 = self.audio_data

            # Convert to bytes
            audio_bytes = audio_int16.tobytes()

            self.progress_percent.emit(30)

            # Run transcription through coordinator
            result: TranscriptionResult = self.coordinator.transcribe(
                audio_bytes, language=self.language
            )

            self.progress_percent.emit(90)

            if result.text:
                self.progress.emit("Transcription completed!")
                self.progress_percent.emit(100)
                self.finished.emit(result.text)
            else:
                self.progress.emit("No voice detected")
                self.finished.emit("No voice detected")

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.error.emit(str(e))
        finally:
            self._is_running = False

    def isRunning(self) -> bool:
        """Check if worker is still running"""
        return self._is_running and super().isRunning()


class CoordinatorTranscriber(BaseTranscriber):
    """
    Transcriber that uses BackendCoordinator for multi-backend support.

    This class provides the same interface as WhisperTranscriber but routes
    to the appropriate backend (Whisper, Granite, Liquid, Qwen) based on the
    active model's backend type.
    """

    def __init__(self, settings):
        """
        Initialize the CoordinatorTranscriber.

        Args:
            settings: Settings object for accessing configuration
        """
        super().__init__()
        self.settings = settings
        self.coordinator: BackendCoordinator = get_coordinator()
        self._current_model_name: Optional[str] = None
        self._current_language: Optional[str] = None
        self._worker: Optional[CoordinatorTranscriptionWorker] = None

    def is_model_loaded(self) -> bool:
        """Check if a model is loaded and ready.

        Returns:
            True if a model is loaded, False otherwise.
        """
        return self._current_model_name is not None

    def _load_current_model(self):
        """Load the current model based on settings"""
        model_name = self.settings.get("model")
        if not model_name:
            logger.warning("No model configured in settings")
            return

        try:
            self._load_model(model_name)
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            # Don't raise - allow lazy loading on first transcription

    def _load_model(self, model_name: str):
        """Load a specific model through the coordinator"""
        logger.info(f"Loading model via coordinator: {model_name}")

        # Check if model is already loaded
        if self._current_model_name == model_name:
            logger.info(f"Model {model_name} already loaded")
            return

        # Unload current model if different
        if self._current_model_name:
            try:
                self.coordinator.unload_model()
                logger.info(f"Unloaded previous model: {self._current_model_name}")
            except Exception as e:
                logger.warning(f"Error unloading previous model: {e}")

        # Load new model with device from settings
        try:
            device = self.settings.get("device", "auto")
            self.coordinator.load_model(model_name, device)
            self._current_model_name = model_name
            logger.info(f"Successfully loaded model: {model_name} on device: {device}")
            self.model_changed.emit(model_name)
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    def update_model(self, model_name: Optional[str] = None) -> bool:
        """
        Update to a new model.

        Args:
            model_name: Model to load, or None to use settings

        Returns:
            True if model was changed, False otherwise
        """
        if model_name is None:
            model_name = self.settings.get("model")

        if model_name == self._current_model_name:
            logger.info(f"Model {model_name} already loaded")
            return False

        try:
            self._load_model(model_name)
            return True
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
            self.transcription_error.emit(f"Failed to load model: {e}")
            return False

    def update_language(self, language: Optional[str] = None) -> bool:
        """
        Update the transcription language.

        Args:
            language: Language code, or None to use settings

        Returns:
            True if language was changed, False otherwise
        """
        if language is None:
            language = self.settings.get("language", "auto")

        if language == self._current_language:
            return False

        self._current_language = language
        logger.info(f"Language updated to: {language}")
        self.language_changed.emit(language)
        return True

    def reload_model_if_needed(self) -> bool:
        """
        Check if model needs reloading based on settings changes.

        Returns:
            True if model was reloaded, False otherwise
        """
        model_name = self.settings.get("model")

        if model_name != self._current_model_name:
            logger.info(
                f"Model changed from {self._current_model_name} to {model_name}"
            )
            return self.update_model(model_name)

        return False

    def transcribe(self, audio_data: bytes, language: Optional[str] = None):
        """
        Transcribe audio data (synchronous, for testing/simple use).

        Args:
            audio_data: Raw audio bytes (16kHz PCM)
            language: Optional language code
        """
        try:
            # Ensure model is loaded
            self.reload_model_if_needed()

            if not self._current_model_name:
                raise RuntimeError("No model loaded")

            # Use specified language or current setting
            if language is None:
                language = self._current_language

            self.transcription_progress.emit("Processing audio...")

            # Run transcription
            result = self.coordinator.transcribe(audio_data, language)

            if result.text:
                self.transcription_finished.emit(result.text)
            else:
                self.transcription_finished.emit("No voice detected")

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.transcription_error.emit(str(e))

    def transcribe_audio(self, normalized_audio_data: np.ndarray):
        """
        Transcribe normalized audio data asynchronously.

        This is the main method used by the application. It starts a worker
        thread to avoid blocking the UI.

        Args:
            normalized_audio_data: Audio as float32 numpy array [-1.0, 1.0]
        """
        # Check if transcription already in progress
        if self._worker and self._worker.isRunning():
            logger.warning("Transcription already in progress, ignoring new request")
            return

        # Ensure model is loaded
        try:
            model_changed = self.reload_model_if_needed()
            if model_changed:
                logger.info(f"Model reloaded to: {self._current_model_name}")
        except Exception as e:
            logger.error(f"Failed to load model for transcription: {e}")
            self.transcription_error.emit(f"Failed to load model: {e}")
            return

        if not self._current_model_name:
            self.transcription_error.emit(
                "No model loaded. Please download a model in Settings."
            )
            return

        # Create and start worker thread
        language = self._current_language or self.settings.get("language", "auto")

        self._worker = CoordinatorTranscriptionWorker(
            self.coordinator, normalized_audio_data, language
        )

        # Connect signals
        self._worker.progress.connect(self.transcription_progress)
        self._worker.progress_percent.connect(self.transcription_progress_percent)
        self._worker.finished.connect(self.transcription_finished)
        self._worker.error.connect(self.transcription_error)

        # Start transcription
        self.transcription_progress.emit("Starting transcription...")
        self.transcription_progress_percent.emit(0)
        self._worker.start()

    def cleanup(self):
        """Clean up resources"""
        if self._worker and self._worker.isRunning():
            logger.warning("Waiting for transcription to complete before cleanup...")
            self._worker.wait(5000)  # Wait up to 5 seconds

        try:
            if self._current_model_name:
                self.coordinator.unload_model()
                logger.info(f"Unloaded model: {self._current_model_name}")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

        # Force garbage collection
        gc.collect()
