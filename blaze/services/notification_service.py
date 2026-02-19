"""Notification service for Syllablaze.

Provides a decoupled way to emit notification requests. The UI layer
subscribes to these signals and handles the actual notification display.
This removes the clipboard→UI dependency that was causing coupling issues.
"""

from PyQt6.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class NotificationService(QObject):
    """Decoupled notification emitter.

    Services and managers emit notification requests through this service
    rather than directly calling UI methods. The UI layer (SyllablazeOrchestrator)
    subscribes to these signals and decides how to display notifications.

    This decouples clipboard operations from UI concerns.

    Signals:
        notification_requested(title, message, icon): Request to show a notification
        transcription_complete(text): Specific signal for transcription completion
        error_occurred(title, message): Request to show an error notification
    """

    notification_requested = pyqtSignal(str, str, object)  # title, message, icon
    transcription_complete = pyqtSignal(str)  # transcribed text
    error_occurred = pyqtSignal(str, str)  # title, message

    def __init__(self, settings=None):
        """Initialize the notification service.

        Parameters:
        -----------
        settings : Settings, optional
            Application settings instance
        """
        super().__init__()
        self.settings = settings
        logger.info("NotificationService: Initialized")

    def notify(self, title, message, icon=None):
        """Emit a notification request.

        Parameters:
        -----------
        title : str
            Notification title
        message : str
            Notification body text
        icon : QIcon, optional
            Icon to display with notification
        """
        logger.debug(
            f"NotificationService: Emitting notification - {title}: {message[:50]}..."
        )
        self.notification_requested.emit(title, message, icon)

    def notify_transcription_complete(self, text):
        """Emit transcription complete notification.

        This is a convenience method for the common case of transcription
        completion notifications.

        Parameters:
        -----------
        text : str
            The transcribed text (will be truncated for display)
        """
        # Truncate text for notification if too long
        display_text = text
        if len(text) > 100:
            display_text = text[:100] + "..."

        logger.debug(
            f"NotificationService: Emitting transcription complete - {display_text[:50]}..."
        )
        self.transcription_complete.emit(display_text)

    def notify_error(self, title, message):
        """Emit an error notification.

        Parameters:
        -----------
        title : str
            Error title
        message : str
            Error message
        """
        logger.debug(f"NotificationService: Emitting error - {title}: {message}")
        self.error_occurred.emit(title, message)
