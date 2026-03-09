"""
Backend Health Tracking

Tracks the health status of each backend for user feedback and
to avoid repeatedly trying failed backends.
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime


class BackendHealthStatus(Enum):
    """Health status for a backend."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    MISSING_DEPENDENCIES = "missing_dependencies"


@dataclass
class BackendHealth:
    """Health information for a backend."""

    backend_name: str
    status: BackendHealthStatus
    last_check: datetime
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0


class BackendHealthRegistry:
    """Registry for tracking backend health status.

        This is a singleton that persists across the application lifetime
    to track which backends are working and which have failed.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._health: Dict[str, BackendHealth] = {}
            self._initialized = True

    def update_status(
        self,
        backend_name: str,
        status: BackendHealthStatus,
        error: Optional[str] = None,
    ):
        """Update the health status of a backend."""
        now = datetime.now()

        if backend_name not in self._health:
            self._health[backend_name] = BackendHealth(
                backend_name=backend_name,
                status=status,
                last_check=now,
                last_error=error,
            )
        else:
            health = self._health[backend_name]
            health.status = status
            health.last_check = now

            if status == BackendHealthStatus.FAILED:
                health.consecutive_failures += 1
                health.last_error = error
            elif status == BackendHealthStatus.HEALTHY:
                health.consecutive_failures = 0
                health.last_success = now
                health.last_error = None

    def get_status(self, backend_name: str) -> BackendHealthStatus:
        """Get the current health status of a backend."""
        if backend_name not in self._health:
            return BackendHealthStatus.UNKNOWN
        return self._health[backend_name].status

    def is_healthy(self, backend_name: str) -> bool:
        """Check if a backend is currently healthy."""
        status = self.get_status(backend_name)
        return status in (BackendHealthStatus.HEALTHY, BackendHealthStatus.DEGRADED)

    def is_failed(self, backend_name: str) -> bool:
        """Check if a backend has failed."""
        status = self.get_status(backend_name)
        return status == BackendHealthStatus.FAILED

    def get_last_error(self, backend_name: str) -> Optional[str]:
        """Get the last error message for a failed backend."""
        if backend_name not in self._health:
            return None
        return self._health[backend_name].last_error

    def get_all_health(self) -> Dict[str, BackendHealth]:
        """Get health status for all backends."""
        return dict(self._health)

    def clear(self):
        """Clear all health status (for testing)."""
        self._health.clear()
