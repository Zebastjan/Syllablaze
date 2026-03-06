"""
System Resource Detection

Provides hardware detection capabilities for recommending appropriate models.
"""

from blaze.system.resource_detector import (
    SystemResources,
    ResourceDetector,
    detect_resources,
    get_resource_detector,
)

__all__ = [
    "SystemResources",
    "ResourceDetector",
    "detect_resources",
    "get_resource_detector",
]
