"""
Abstract base class for all transcriber implementations.

This module provides the BaseTranscriber base class that defines
a common interface for all speech-to-text transcriber implementations.
This ensures that all transcribers implement the same interface,
preventing regressions when new transcriber types are added.
"""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal


class BaseTranscriber(QObject):
    """
    Base class for all speech-to-text transcribers.

    All transcriber implementations (WhisperTranscriber, CoordinatorTranscriber,
    or any future implementations) must inherit from this class and implement
    all abstract methods. This ensures consistent interface across all backends.

    Signals:
        transcription_progress(str): Progress message during transcription
        transcription_progress_percent(int): Progress percentage (0-100)
        transcription_finished(str): Emitted when transcription completes with text
        transcription_error(str): Emitted when transcription fails with error message
        model_changed(str): Emitted when model is changed
        language_changed(str): Emitted when language is changed
    """

    # Signals that all transcribers must emit
    transcription_progress = pyqtSignal(str)
    transcription_progress_percent = pyqtSignal(int)
    transcription_finished = pyqtSignal(str)
    transcription_error = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)

    def __init__(self):
        """Initialize the base transcriber."""
        super().__init__()
        self._current_model_name: Optional[str] = None
        self._current_language: Optional[str] = None

    @property
    def current_model_name(self) -> Optional[str]:
        """Get the name of the currently loaded model."""
        return self._current_model_name

    @current_model_name.setter
    def current_model_name(self, value: Optional[str]):
        """Set the current model name."""
        self._current_model_name = value

    @property
    def current_language(self) -> Optional[str]:
        """Get the current language setting."""
        return self._current_language

    @current_language.setter
    def current_language(self, value: Optional[str]):
        """Set the current language."""
        self._current_language = value

    def is_model_loaded(self) -> bool:
        """
        Check if a model is loaded and ready for transcription.

        Returns:
            True if a model is loaded and ready, False otherwise.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement is_model_loaded()")

    def update_model(self, model_name: Optional[str] = None) -> bool:
        """
        Update/load a model.

        Args:
            model_name: Model to load, or None to use settings.

        Returns:
            True if model was changed/loaded, False otherwise.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement update_model()")

    def update_language(self, language: Optional[str] = None) -> bool:
        """
        Update the transcription language.

        Args:
            language: Language code, or None to use settings.

        Returns:
            True if language was changed, False otherwise.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement update_language()")

    def transcribe_audio(self, normalized_audio_data):
        """
        Transcribe normalized audio data asynchronously.

        Args:
            normalized_audio_data: Audio as float32 numpy array [-1.0, 1.0].

        Note:
            This method should start transcription in a background thread
            and emit signals for progress and completion.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement transcribe_audio()")

    def reload_model_if_needed(self) -> bool:
        """
        Check if model needs reloading based on settings changes.

        Returns:
            True if model was reloaded, False otherwise.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement reload_model_if_needed()")

    def cleanup(self):
        """
        Clean up resources. Override if needed.

        This is a concrete method with default no-op behavior.
        Subclasses should override if they need cleanup.
        """
        pass
