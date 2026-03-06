"""
System Resource Detector

Detects hardware capabilities (RAM, GPU, CPU) to help recommend
appropriate models for the user's system.
"""

import psutil
import glob
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SystemResources:
    """Container for system hardware information"""

    total_ram_gb: float
    available_ram_gb: float
    cpu_count: int
    cpu_freq_mhz: Optional[float]
    gpu_available: bool
    gpu_count: int = 0
    gpu_memory_gb: Optional[List[float]] = None
    gpu_names: Optional[List[str]] = None
    is_laptop: bool = False

    def can_run_model(
        self, min_ram_gb: float, min_vram_gb: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Check if system can run a model with given requirements.

        Returns:
            Tuple of (can_run: bool, reason: str)
        """
        # Check RAM
        if self.available_ram_gb < min_ram_gb:
            return (
                False,
                f"Needs {min_ram_gb}GB RAM available, have {self.available_ram_gb:.1f}GB",
            )

        # Check VRAM if required
        if min_vram_gb is not None:
            if not self.gpu_available:
                return False, f"Needs GPU with {min_vram_gb}GB VRAM, no GPU detected"

            total_vram = sum(self.gpu_memory_gb) if self.gpu_memory_gb else 0
            if total_vram < min_vram_gb:
                return False, f"Needs {min_vram_gb}GB VRAM, have {total_vram:.1f}GB"

        return True, "Compatible with your system"

    def get_recommended_tier(self) -> str:
        """
        Get recommended model tier based on available resources.

        Returns one of: 'ultra_light', 'light', 'medium', 'heavy'
        """
        if self.available_ram_gb < 2:
            return "ultra_light"
        elif self.available_ram_gb < 4:
            return "light"
        elif self.available_ram_gb < 8:
            return "medium"
        else:
            return "heavy"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization (e.g., to QML)"""
        return {
            "total_ram_gb": round(self.total_ram_gb, 1),
            "available_ram_gb": round(self.available_ram_gb, 1),
            "cpu_count": self.cpu_count,
            "cpu_freq_mhz": self.cpu_freq_mhz,
            "gpu_available": self.gpu_available,
            "gpu_count": self.gpu_count,
            "gpu_memory_gb": self.gpu_memory_gb,
            "gpu_names": self.gpu_names,
            "is_laptop": self.is_laptop,
            "recommended_tier": self.get_recommended_tier(),
        }


class ResourceDetector:
    """Detects system hardware resources"""

    def detect(self) -> SystemResources:
        """
        Detect system resources.

        Returns:
            SystemResources with detected hardware info
        """
        logger.info("Detecting system resources...")

        # RAM
        mem = psutil.virtual_memory()
        total_ram = mem.total / (1024**3)
        available_ram = mem.available / (1024**3)
        logger.info(f"RAM: {available_ram:.1f}GB available / {total_ram:.1f}GB total")

        # CPU
        cpu_count = psutil.cpu_count(logical=True)
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_freq_mhz = cpu_freq.max if cpu_freq else None
        except:
            cpu_freq_mhz = None
        logger.info(f"CPU: {cpu_count} cores @ {cpu_freq_mhz or 'unknown'} MHz")

        # GPU detection (via PyTorch)
        gpu_available, gpu_count, gpu_memory, gpu_names = self._detect_gpu()
        if gpu_available:
            logger.info(f"GPU: {gpu_count} device(s) detected")
            for i, (name, mem_gb) in enumerate(zip(gpu_names or [], gpu_memory or [])):
                logger.info(f"  GPU {i}: {name} ({mem_gb:.1f}GB)")
        else:
            logger.info("GPU: Not detected")

        # Laptop detection
        is_laptop = self._detect_laptop()
        logger.info(f"System type: {'Laptop' if is_laptop else 'Desktop'}")

        return SystemResources(
            total_ram_gb=total_ram,
            available_ram_gb=available_ram,
            cpu_count=cpu_count,
            cpu_freq_mhz=cpu_freq_mhz,
            gpu_available=gpu_available,
            gpu_count=gpu_count,
            gpu_memory_gb=gpu_memory,
            gpu_names=gpu_names,
            is_laptop=is_laptop,
        )

    def _detect_gpu(
        self,
    ) -> Tuple[bool, int, Optional[List[float]], Optional[List[str]]]:
        """
        Detect GPU using PyTorch.

        Returns:
            Tuple of (available, count, memory_list, name_list)
        """
        try:
            import torch

            if not torch.cuda.is_available():
                return False, 0, None, None

            gpu_count = torch.cuda.device_count()
            gpu_memory = []
            gpu_names = []

            for i in range(gpu_count):
                # Get device name
                name = torch.cuda.get_device_name(i)
                gpu_names.append(name)

                # Get memory
                props = torch.cuda.get_device_properties(i)
                mem_gb = props.total_memory / (1024**3)
                gpu_memory.append(mem_gb)

            return True, gpu_count, gpu_memory, gpu_names

        except ImportError:
            logger.debug("PyTorch not available for GPU detection")
            return False, 0, None, None
        except Exception as e:
            logger.warning(f"Error detecting GPU: {e}")
            return False, 0, None, None

    def _detect_laptop(self) -> bool:
        """
        Detect if system is a laptop.

        Uses multiple heuristics:
        1. Check for battery presence (Linux)
        2. Check for AC adapter (Linux)
        3. Check chassis type (if available)

        Returns:
            True if laptop is detected
        """
        try:
            # Method 1: Check for battery
            battery_paths = glob.glob("/sys/class/power_supply/BAT*")
            if battery_paths:
                return True

            # Method 2: Check chassis type
            try:
                with open("/sys/class/dmi/id/chassis_type", "r") as f:
                    chassis_type = int(f.read().strip())
                    # Chassis types 8-11 are portable/laptop types
                    # See: https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.0.0.pdf
                    if 8 <= chassis_type <= 11:
                        return True
            except (FileNotFoundError, ValueError):
                pass

            # Method 3: Check for common laptop indicators in DMI
            try:
                with open("/sys/class/dmi/id/product_name", "r") as f:
                    product_name = f.read().lower()
                    laptop_indicators = [
                        "laptop",
                        "notebook",
                        "thinkpad",
                        " Latitude ",
                        "xps",
                    ]
                    if any(
                        indicator in product_name for indicator in laptop_indicators
                    ):
                        return True
            except FileNotFoundError:
                pass

        except Exception as e:
            logger.debug(f"Error detecting laptop: {e}")

        return False

    def get_best_model_for_system(
        self, registry, language: Optional[str] = None
    ) -> Optional:
        """
        Get the best model recommendation for the current system.

        Args:
            registry: ModelRegistry class
            language: Optional language filter

        Returns:
            ModelCapability for the best model, or None
        """
        resources = self.detect()

        # Get compatible models
        compatible = registry.get_compatible_models(
            available_ram_gb=resources.available_ram_gb,
            gpu_available=resources.gpu_available,
            gpu_memory_gb=resources.gpu_memory_gb,
            language=language,
        )

        if not compatible:
            logger.warning("No compatible models found for this system")
            return None

        # Get recommended models (those that meet recommended RAM)
        recommended = [
            m for m in compatible if resources.available_ram_gb >= m.recommended_ram_gb
        ]

        if recommended:
            # Pick the largest (most capable) recommended model
            # Sort by size_mb descending and pick first
            best = max(recommended, key=lambda m: m.size_mb)
        else:
            # Fall back to largest compatible model
            best = max(compatible, key=lambda m: m.size_mb)

        logger.info(f"Best model for system: {best.name} ({best.model_id})")
        return best


# Singleton instance for application-wide use
_resource_detector: Optional[ResourceDetector] = None


def get_resource_detector() -> ResourceDetector:
    """Get the singleton ResourceDetector instance"""
    global _resource_detector
    if _resource_detector is None:
        _resource_detector = ResourceDetector()
    return _resource_detector


def detect_resources() -> SystemResources:
    """Convenience function to detect system resources"""
    return get_resource_detector().detect()
