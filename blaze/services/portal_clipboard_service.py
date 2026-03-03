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
from typing import Optional

from PyQt6.QtCore import QObject

logger = logging.getLogger(__name__)


class WlClipboardService(QObject):
    """Provide a wl-copy based clipboard implementation."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._wl_copy_path = shutil.which("wl-copy")
        if self._wl_copy_path:
            logger.info("WlClipboardService: wl-copy detected at %s", self._wl_copy_path)
        else:
            logger.info("WlClipboardService: wl-copy not found; portal path disabled")

    # ------------------------------------------------------------------
    # Capability detection
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Return ``True`` if wl-copy is available."""
        return self._wl_copy_path is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_text(self, text: str, parent_window: str | None = None) -> bool:
        """Copy ``text`` to the clipboard via wl-copy."""
        if not self.is_available():
            return False

        if text is None:
            text = ""

        try:
            result = subprocess.run(
                [self._wl_copy_path, "--type", "text/plain;charset=utf-8"],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            if result.stderr:
                logger.debug(
                    "WlClipboardService: wl-copy produced stderr: %s",
                    result.stderr.decode("utf-8", errors="ignore"),
                )
            return True
        except FileNotFoundError:  # pragma: no cover - defensive
            logger.warning(
                "WlClipboardService: wl-copy disappeared at runtime"
            )
            self._wl_copy_path = None
        except subprocess.CalledProcessError as exc:
            logger.error(
                "WlClipboardService: wl-copy failed (returncode=%s, stderr=%s)",
                exc.returncode,
                exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else "",
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("WlClipboardService: wl-copy invocation error: %s", exc)

        return False

    def get_text(self) -> Optional[str]:
        """wl-clipboard does not expose read via wl-copy; report unavailable."""
        return None

    def clear(self) -> bool:
        """Clearing via wl-copy is equivalent to copying an empty string."""
        return self.set_text("")
