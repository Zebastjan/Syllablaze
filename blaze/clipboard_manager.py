"""Clipboard manager for Syllablaze.

Pure clipboard service with no UI dependencies. Uses ClipboardPersistenceService
for Wayland-compatible clipboard ownership.

Signals:
    transcription_copied(text): Emitted when transcription text is copied
    clipboard_error(error): Emitted when clipboard operation fails
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
import subprocess
import logging

from .services.clipboard_persistence_service import ClipboardPersistenceService
from .services.portal_clipboard_service import WlClipboardService

logger = logging.getLogger(__name__)


class ClipboardManager(QObject):
    """Manages clipboard operations for transcribed text.

    This is a pure service with no UI dependencies. It delegates clipboard
    persistence to ClipboardPersistenceService and emits signals for success
    and error conditions. The orchestrator subscribes to these signals and
    handles notifications separately.

    Signals:
        transcription_copied(text): Emitted when text is copied to clipboard
        clipboard_error(error): Emitted when clipboard operation fails
    """

    transcription_copied = pyqtSignal(str)
    clipboard_error = pyqtSignal(str)

    def __init__(
        self,
        settings=None,
        persistence_service: ClipboardPersistenceService | None = None,
        portal_service: WlClipboardService | None = None,
    ):
        """Initialize clipboard manager.

        Parameters:
        -----------
        settings : Settings, optional
            Application settings instance
        persistence_service : ClipboardPersistenceService, optional
            Existing persistence service instance. If not provided, one will be created.
        portal_service : WlClipboardService, optional
            Optional wl-copy based clipboard service for focus-independent copy.
        """
        super().__init__()
        self.settings = settings

        self._persistence_service = persistence_service
        self._portal_service = portal_service or WlClipboardService()

        if self._persistence_service:
            # Wire persistence service signals through to our handlers
            self._persistence_service.clipboard_set.connect(
                self._on_persistence_clipboard_set
            )
            self._persistence_service.clipboard_error.connect(
                self._on_persistence_clipboard_error
            )
        else:
            logger.debug(
                "ClipboardManager: No Qt persistence service configured (portal_only=%s)",
                self._portal_service.is_available() if self._portal_service else False,
            )

        self._diagnostics_enabled = False
        self._diagnostics_retry_limit = 2
        self._diagnostics_preview_chars = 80
        self._last_clipboard_text = ""

        self._update_diagnostics_state(initial=True)

        logger.info("ClipboardManager: Initialized (pure service, no UI deps)")

    @pyqtSlot(str)
    def copy_to_clipboard(self, text):
        """Copy transcribed text to clipboard.

        Delegates to ClipboardPersistenceService and emits signals for result.
        No UI operations - notifications are handled by the orchestrator via signals.

        Parameters:
        -----------
        text : str
            Transcribed text to copy

        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        if not text:
            logger.warning("ClipboardManager: Received empty text, skipping")
            return False

        portal_used = False
        if self._portal_service and self._portal_service.is_available():
            logger.debug("ClipboardManager: Attempting wl-copy clipboard set")
            portal_used = self._portal_service.set_text(text)
            if portal_used:
                logger.info(
                    "ClipboardManager: Copied transcription via wl-copy: %s...",
                    text[:50],
                )
                self.transcription_copied.emit(text)
                return True

        diagnostics_enabled = self._update_diagnostics_state()
        success = False

        if self._persistence_service:
            success = self._persistence_service.set_text(text)
        elif not portal_used:
            logger.error(
                "ClipboardManager: No clipboard backend available (text not copied)"
            )

        if success:
            logger.info(f"ClipboardManager: Copied transcription: {text[:50]}...")
            if diagnostics_enabled and self._persistence_service:
                self._schedule_clipboard_verification(text)
        else:
            logger.error(
                "ClipboardManager: Failed to copy to clipboard (portal_used=%s)",
                portal_used,
            )

        return success

    def _normalize_bool(self, value):
        """Normalize various truthy values to bool."""
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "on"}
        return bool(value)

    def _apply_diagnostics_enabled(self, enabled, reason="runtime"):
        enabled = bool(enabled)
        if enabled == self._diagnostics_enabled:
            return enabled

        self._diagnostics_enabled = enabled
        state = "enabled" if enabled else "disabled"
        logger.info(f"Clipboard diagnostics {state} ({reason})")

        if hasattr(self._persistence_service, "set_diagnostics_enabled"):
            self._persistence_service.set_diagnostics_enabled(enabled)

        if not enabled:
            self._last_clipboard_text = ""

        return enabled

    def _update_diagnostics_state(self, initial=False):
        """Refresh diagnostics flag from settings."""
        enabled = False
        if self.settings is not None:
            try:
                enabled = self._normalize_bool(
                    self.settings.get("clipboard_diagnostics", False)
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "ClipboardManager: Failed to read diagnostics setting: %s",
                    exc,
                )
        if enabled and not self._persistence_service:
            logger.debug(
                "ClipboardManager: Disabling clipboard diagnostics (no persistence backend)"
            )
            enabled = False
        reason = "initial" if initial else "runtime"
        return self._apply_diagnostics_enabled(enabled, reason=reason)

    def on_setting_changed(self, key, value):
        """React to SettingsBridge setting changes."""
        if key != "clipboard_diagnostics":
            return
        enabled = self._normalize_bool(value)
        self._apply_diagnostics_enabled(enabled, reason="settings-change")

    def _schedule_clipboard_verification(self, expected_text, attempt=0):
        if (
            not self._diagnostics_enabled
            or not expected_text
            or not self._persistence_service
        ):
            return

        delay_ms = 75 if attempt == 0 else 200
        QTimer.singleShot(
            delay_ms,
            lambda text=expected_text, attempt_idx=attempt: (
                self._verify_clipboard_contents(text, attempt_idx)
            ),
        )

    def _verify_clipboard_contents(self, expected_text, attempt):
        current_text = self.get_text() or ""
        expected_text = expected_text or ""

        if current_text == expected_text:
            if self._diagnostics_enabled:
                logger.debug(
                    "Clipboard diagnostics: verification succeeded on attempt %s",
                    attempt + 1,
                )
            self._last_clipboard_text = current_text
            return

        preview_expected = expected_text[: self._diagnostics_preview_chars]
        preview_actual = current_text[: self._diagnostics_preview_chars]
        logger.warning(
            "Clipboard diagnostics: mismatch (attempt %s). expected=%r actual=%r",
            attempt + 1,
            preview_expected,
            preview_actual,
        )

        if attempt < self._diagnostics_retry_limit:
            next_attempt = attempt + 1
            logger.info(
                "Clipboard diagnostics: retrying clipboard copy (attempt %s of %s)",
                next_attempt + 1,
                self._diagnostics_retry_limit + 1,
            )
            self._persistence_service.set_text(expected_text)
            self._schedule_clipboard_verification(expected_text, next_attempt)
        else:
            error_msg = "Clipboard verification failed after retries"
            logger.error("Clipboard diagnostics: %s", error_msg)
            self.clipboard_error.emit(error_msg)

    @pyqtSlot(str)
    def _on_persistence_clipboard_set(self, text):
        self._last_clipboard_text = text or ""
        if self._diagnostics_enabled:
            preview = self._last_clipboard_text[: self._diagnostics_preview_chars]
            logger.debug(
                "Clipboard diagnostics: persistence service reported clipboard set (preview=%r)",
                preview,
            )
        self.transcription_copied.emit(text)

    @pyqtSlot(str)
    def _on_persistence_clipboard_error(self, error):
        if self._diagnostics_enabled:
            logger.error("Clipboard diagnostics: persistence error: %s", error)
        self.clipboard_error.emit(error)

    def paste_text(self, text):
        """Copy text to clipboard for auto-paste functionality.

        Copies text to clipboard and optionally pastes to active window.

        Parameters:
        -----------
        text : str
            Text to copy
        """
        if not text:
            logger.warning("ClipboardManager: Received empty text for paste, skipping")
            return

        logger.info(f"ClipboardManager: Copying for paste: {text[:50]}...")

        # Copy to clipboard
        portal_used = False
        if self._portal_service and self._portal_service.is_available():
            portal_used = self._portal_service.set_text(text)
            if portal_used:
                if self._should_paste_to_active_window():
                    self._paste_to_active_window()
                return

        diagnostics_enabled = self._update_diagnostics_state()
        success = False
        if self._persistence_service:
            success = self._persistence_service.set_text(text)
        elif not portal_used:
            logger.error(
                "ClipboardManager: No clipboard backend available for paste text"
            )

        if success:
            if diagnostics_enabled and self._persistence_service:
                self._schedule_clipboard_verification(text)
            if self._should_paste_to_active_window():
                self._paste_to_active_window()
        else:
            logger.error(
                "ClipboardManager: Failed to copy text for paste (portal_used=%s)",
                portal_used,
            )

    def _paste_to_active_window(self):
        """Simulate Ctrl+V to paste to active window."""
        try:
            subprocess.run(["xdotool", "key", "ctrl+v"], check=True)
            logger.info("ClipboardManager: Pasted to active window")
        except Exception as e:
            logger.error(f"ClipboardManager: Failed to paste to active window: {e}")

    def _should_paste_to_active_window(self):
        """Check if should auto-paste to active window."""
        # TODO: Get this from settings when the feature is implemented
        return False

    def get_text(self):
        """Get text from clipboard.

        Returns:
        --------
        str
            Current clipboard text or empty string
        """
        # Portal service doesn't currently provide read access; fall back
        return self._persistence_service.get_text() if self._persistence_service else ""

    def clear(self):
        """Clear the clipboard.

        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        if self._portal_service and self._portal_service.is_available():
            if self._portal_service.clear():
                return True
        if self._persistence_service:
            return self._persistence_service.clear()
        return False

    def shutdown(self):
        """Shutdown the clipboard manager gracefully."""
        logger.info("ClipboardManager: Shutting down")
        if hasattr(self, "_diagnostics_timer") and self._diagnostics_timer:
            self._diagnostics_timer.stop()
            self._diagnostics_timer.deleteLater()
            self._diagnostics_timer = None

        if self._persistence_service:
            self._persistence_service.shutdown()

        if self._portal_service:
            self._portal_service.shutdown()
