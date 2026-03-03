"""Wayland clipboard fallback using ``wl-copy`` from wl-clipboard.

When the compositor refuses focus-dependent clipboard ownership, we shell out
to ``wl-copy`` which talks to the Wayland data-control protocol directly. This
keeps the text focused-independent while still allowing us to fall back to the
Qt clipboard APIs when the utility is unavailable.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import signal
from typing import Optional

from PyQt6.QtCore import QObject

logger = logging.getLogger(__name__)


class WlClipboardService(QObject):
    """Provide a wl-copy based clipboard implementation.

    Uses a persistent wl-copy process that maintains clipboard ownership.
    Only one wl-copy process is kept alive at a time - old processes are
    terminated before starting new ones.
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._wl_copy_path = shutil.which("wl-copy")
        self._current_process: Optional[subprocess.Popen] = None
        if self._wl_copy_path:
            logger.info(
                "WlClipboardService: wl-copy detected at %s", self._wl_copy_path
            )
        else:
            logger.info("WlClipboardService: wl-copy not found; portal path disabled")

    def __del__(self):
        """Cleanup any running wl-copy process on destruction."""
        self._kill_current_process()

    # ------------------------------------------------------------------
    # Capability detection
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Return ``True`` if wl-copy is available."""
        return self._wl_copy_path is not None

    # ------------------------------------------------------------------
    # Process management
    # ------------------------------------------------------------------
    def _kill_current_process(self):
        """Kill the current wl-copy process if it exists."""
        if self._current_process is None:
            return

        try:
            # Check if process is still running
            if self._current_process.poll() is None:
                logger.debug(
                    "WlClipboardService: Terminating previous wl-copy process (PID %s)",
                    self._current_process.pid,
                )
                # Send SIGTERM first for graceful shutdown
                self._current_process.terminate()
                try:
                    # Wait briefly for graceful shutdown
                    self._current_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    logger.debug("WlClipboardService: Force killing wl-copy process")
                    self._current_process.kill()
                    self._current_process.wait()
        except Exception as e:
            logger.debug("WlClipboardService: Error terminating wl-copy process: %s", e)
        finally:
            self._current_process = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_text(self, text: str | None, parent_window: str | None = None) -> bool:
        """Copy ``text`` to the clipboard via wl-copy.

        Starts wl-copy in the background (non-blocking) to maintain clipboard
        ownership. Kills any previous wl-copy process first.
        """
        if not self.is_available():
            return False

        if text is None:
            text = ""

        try:
            # Kill any existing wl-copy process first
            self._kill_current_process()

            # Start new wl-copy process (non-blocking)
            # wl-copy will daemonize itself and stay running to maintain clipboard
            self._current_process = subprocess.Popen(
                [str(self._wl_copy_path), "--type", "text/plain;charset=utf-8"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process group
            )

            # Write text to wl-copy's stdin
            if self._current_process.stdin is not None:
                try:
                    self._current_process.stdin.write(text.encode("utf-8"))
                    self._current_process.stdin.close()
                except BrokenPipeError:
                    # Process may have already exited (error case)
                    logger.warning(
                        "WlClipboardService: wl-copy exited before receiving data"
                    )
                    self._current_process = None
                    return False

            logger.debug(
                "WlClipboardService: wl-copy started (PID %s) to maintain clipboard",
                self._current_process.pid,
            )
            return True

        except FileNotFoundError:  # pragma: no cover - defensive
            logger.warning("WlClipboardService: wl-copy disappeared at runtime")
            self._wl_copy_path = None
            self._current_process = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("WlClipboardService: wl-copy invocation error: %s", exc)
            self._current_process = None

        return False

        if text is None:
            text = ""

        try:
            # Kill any existing wl-copy process first
            self._kill_current_process()

            # Start new wl-copy process (non-blocking)
            # wl-copy will daemonize itself and stay running to maintain clipboard
            self._current_process = subprocess.Popen(
                [self._wl_copy_path, "--type", "text/plain;charset=utf-8"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process group
            )

            # Write text to wl-copy's stdin
            try:
                self._current_process.stdin.write(text.encode("utf-8"))
                self._current_process.stdin.close()
            except BrokenPipeError:
                # Process may have already exited (error case)
                logger.warning(
                    "WlClipboardService: wl-copy exited before receiving data"
                )
                self._current_process = None
                return False

            logger.debug(
                "WlClipboardService: wl-copy started (PID %s) to maintain clipboard",
                self._current_process.pid,
            )
            return True

        except FileNotFoundError:  # pragma: no cover - defensive
            logger.warning("WlClipboardService: wl-copy disappeared at runtime")
            self._wl_copy_path = None
            self._current_process = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("WlClipboardService: wl-copy invocation error: %s", exc)
            self._current_process = None

        return False

    def get_text(self) -> Optional[str]:
        """wl-clipboard does not expose read via wl-copy; report unavailable."""
        return None

    def clear(self) -> bool:
        """Clearing via wl-copy is equivalent to copying an empty string."""
        return self.set_text("")

    def shutdown(self):
        """Clean up the wl-copy process. Call this during app shutdown."""
        self._kill_current_process()
        logger.info("WlClipboardService: Shutdown complete")
