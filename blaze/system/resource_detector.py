"""
System Resource Detector

Detects hardware capabilities (RAM, GPU, CPU) to help recommend
appropriate models for the user's system.
"""

import psutil
import glob
import logging
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

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
    gpu_vendors: Optional[List[str]] = None  # ['nvidia', 'amd', 'intel']
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
        # Get primary GPU info (first discrete GPU with most VRAM)
        primary_gpu_name = ""
        primary_gpu_vram = 0
        primary_gpu_vendor = ""

        if self.gpu_available and self.gpu_names and len(self.gpu_names) > 0:
            # Find first discrete GPU (non-Intel with VRAM > 0)
            for i, (name, vram, vendor) in enumerate(
                zip(self.gpu_names, self.gpu_memory_gb or [], self.gpu_vendors or [])
            ):
                if vram > 0 and vendor != "intel":
                    primary_gpu_name = name
                    primary_gpu_vram = vram
                    primary_gpu_vendor = vendor
                    break

            # If no discrete GPU found, use the first one
            if not primary_gpu_name:
                primary_gpu_name = self.gpu_names[0]
                primary_gpu_vram = self.gpu_memory_gb[0] if self.gpu_memory_gb else 0
                primary_gpu_vendor = self.gpu_vendors[0] if self.gpu_vendors else ""

        return {
            "total_ram_gb": round(self.total_ram_gb, 1),
            "available_ram_gb": round(self.available_ram_gb, 1),
            "cpu_count": self.cpu_count,
            "cpu_freq_mhz": self.cpu_freq_mhz,
            "gpu_available": self.gpu_available,
            "gpu_count": self.gpu_count,
            "gpu_memory_gb": self.gpu_memory_gb,
            "gpu_names": self.gpu_names,
            "gpu_vendors": self.gpu_vendors,
            "primary_gpu_name": primary_gpu_name,
            "primary_gpu_vram_gb": round(primary_gpu_vram, 1),
            "primary_gpu_vendor": primary_gpu_vendor,
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
        cpu_count = psutil.cpu_count(logical=True) or 1
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_freq_mhz = cpu_freq.max if cpu_freq else None
        except:
            cpu_freq_mhz = None
        logger.info(f"CPU: {cpu_count} cores @ {cpu_freq_mhz or 'unknown'} MHz")

        # GPU detection (via PyTorch)
        gpu_available, gpu_count, gpu_memory, gpu_names, gpu_vendors = (
            self._detect_gpu()
        )
        if gpu_available:
            logger.info(f"GPU: {gpu_count} device(s) detected")
            for i, (name, mem_gb, vendor) in enumerate(
                zip(gpu_names or [], gpu_memory or [], gpu_vendors or [])
            ):
                logger.info(f"  GPU {i}: {name} ({mem_gb:.1f}GB) [{vendor}]")
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
            gpu_vendors=gpu_vendors,
            is_laptop=is_laptop,
        )

    def _detect_gpu(
        self,
    ) -> Tuple[
        bool, int, Optional[List[float]], Optional[List[str]], Optional[List[str]]
    ]:
        """
        Detect GPU using multiple methods for robust cross-vendor support.

        Collects GPUs from ALL sources and merges results to avoid missing
        dedicated GPUs when integrated GPUs are present.

        Priority (for merging, not early return):
        1. PyTorch torch.cuda - most reliable when CUDA is available
        2. nvidia-smi command - system-level NVIDIA detection
        3. NVIDIA (nvidia-ml-py) - most reliable for NVIDIA GPUs
        4. AMD ROCm (rocm-smi or sysfs) - for AMD GPUs
        5. Intel Arc (sysfs) - for Intel GPUs

        Returns:
            Tuple of (available, count, memory_list, name_list, vendor_list)
        """
        all_gpus = []
        detected_ids = set()  # Track unique GPUs by name+memory to avoid duplicates

        def add_gpu(name, memory_gb, vendor):
            """Add GPU if not already detected"""
            # Normalize GPU name for deduplication (remove extra spaces, lowercase)
            normalized_name = " ".join(name.split()).lower()
            # Round memory to nearest integer for deduplication (handles small variations between detection methods)
            # PyTorch might report 12.0 while nvidia-smi reports 11.6 - these should be treated as same GPU
            rounded_mem = round(memory_gb)
            gpu_id = f"{normalized_name}_{rounded_mem}"
            if gpu_id not in detected_ids:
                detected_ids.add(gpu_id)
                all_gpus.append((name, memory_gb, vendor))
                logger.debug(f"Added GPU: {name} ({memory_gb:.1f}GB) [{vendor}]")

        # Try PyTorch first - this often sees dedicated GPUs that sysfs misses
        try:
            result = self._detect_gpu_via_pytorch()
            if result[0]:
                for i in range(result[1]):
                    add_gpu(result[3][i], result[2][i], result[4][i])
        except Exception as e:
            logger.debug(f"PyTorch GPU detection failed: {e}")

        # Try nvidia-smi for accurate NVIDIA detection
        try:
            result = self._detect_nvidia_via_smi()
            if result[0]:
                for i in range(result[1]):
                    add_gpu(result[3][i], result[2][i], result[4][i])
        except Exception as e:
            logger.debug(f"nvidia-smi detection failed: {e}")

        # Try NVIDIA pynvml
        try:
            result = self._detect_nvidia_gpu()
            if result[0]:
                for i in range(result[1]):
                    add_gpu(result[3][i], result[2][i], result[4][i])
        except Exception as e:
            logger.debug(f"pynvml detection failed: {e}")

        # Try AMD ROCm
        try:
            result = self._detect_rocm_gpu()
            if result[0]:
                for i in range(result[1]):
                    add_gpu(result[3][i], result[2][i], result[4][i])
        except Exception as e:
            logger.debug(f"ROCm detection failed: {e}")

        # Try Intel - only add if we don't already have better GPUs
        # Intel integrated often reports 0GB which is misleading
        try:
            result = self._detect_intel_gpu()
            if result[0]:
                for i in range(result[1]):
                    # For Intel integrated with 0GB, note it shares system RAM
                    memory = result[2][i] if result[2][i] > 0 else 0.0
                    add_gpu(result[3][i], memory, result[4][i])
        except Exception as e:
            logger.debug(f"Intel detection failed: {e}")

        if all_gpus:
            # Sort by memory (descending) so best GPU is first
            all_gpus.sort(key=lambda x: x[1], reverse=True)

            gpu_names = [g[0] for g in all_gpus]
            gpu_memory = [g[1] for g in all_gpus]
            gpu_vendors = [g[2] for g in all_gpus]

            logger.info(f"Detected {len(all_gpus)} GPU(s):")
            for name, mem, vendor in all_gpus:
                mem_str = (
                    f"{mem:.1f}GB" if mem > 0 else "Integrated (shares system RAM)"
                )
                logger.info(f"  - {name}: {mem_str} [{vendor}]")

            return True, len(all_gpus), gpu_memory, gpu_names, gpu_vendors

        return False, 0, None, None, None

    def _detect_nvidia_via_smi(
        self,
    ) -> Tuple[
        bool, int, Optional[List[float]], Optional[List[str]], Optional[List[str]]
    ]:
        """Detect NVIDIA GPUs using nvidia-smi command (no library required)"""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                gpu_memory = []
                gpu_names = []
                gpu_vendors = []

                for line in lines:
                    if "," in line:
                        parts = line.split(",")
                        name = parts[0].strip()
                        # Parse memory like "12288 MiB" or "12.3 GiB"
                        mem_str = parts[1].strip()
                        mem_gb = 0.0
                        try:
                            if "MiB" in mem_str:
                                mem_val = float(mem_str.replace("MiB", "").strip())
                                mem_gb = mem_val / 1024
                            elif "GiB" in mem_str:
                                mem_gb = float(mem_str.replace("GiB", "").strip())
                            elif "MB" in mem_str:
                                mem_val = float(mem_str.replace("MB", "").strip())
                                mem_gb = mem_val / 1024
                            elif "GB" in mem_str:
                                mem_gb = float(mem_str.replace("GB", "").strip())
                        except:
                            mem_gb = 0.0

                        gpu_names.append(name)
                        gpu_memory.append(mem_gb)
                        gpu_vendors.append("nvidia")

                if gpu_names:
                    return True, len(gpu_names), gpu_memory, gpu_names, gpu_vendors

        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.debug("nvidia-smi not available")
        except Exception as e:
            logger.debug(f"Error detecting NVIDIA GPU via nvidia-smi: {e}")

        return False, 0, None, None, None

    def _detect_nvidia_gpu(
        self,
    ) -> Tuple[
        bool, int, Optional[List[float]], Optional[List[str]], Optional[List[str]]
    ]:
        """Detect NVIDIA GPUs using nvidia-ml-py (pynvml)"""
        try:
            import pynvml

            pynvml.nvmlInit()
            gpu_count = pynvml.nvmlDeviceGetCount()

            if gpu_count == 0:
                return False, 0, None, None, None

            gpu_memory = []
            gpu_names = []
            gpu_vendors = []

            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                # Get name
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                gpu_names.append(name)

                # Get memory (in bytes, convert to GB)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                mem_gb = mem_info.total / (1024**3)
                gpu_memory.append(mem_gb)

                gpu_vendors.append("nvidia")

            return True, gpu_count, gpu_memory, gpu_names, gpu_vendors

        except ImportError:
            logger.debug("nvidia-ml-py not installed")
        except Exception as e:
            logger.debug(f"Error detecting NVIDIA GPU: {e}")

        return False, 0, None, None, None

    def _detect_rocm_gpu(
        self,
    ) -> Tuple[
        bool, int, Optional[List[float]], Optional[List[str]], Optional[List[str]]
    ]:
        """Detect AMD GPUs using ROCm"""
        try:
            # Try rocm-smi first
            import subprocess

            result = subprocess.run(
                ["rocm-smi", "--showproductname", "--showmeminfo", "vram"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse rocm-smi output
                lines = result.stdout.strip().split("\n")
                gpu_names = []
                gpu_memory = []
                gpu_vendors = []

                for line in lines:
                    if "GPU" in line and "VRAM" not in line and "==" not in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            # Extract GPU name
                            name = " ".join(parts[1:])
                            gpu_names.append(name)
                            gpu_vendors.append("amd")
                            # Memory detection via rocm-smi is complex, use sysfs fallback
                            gpu_memory.append(0.0)  # Will be updated below

                if gpu_names:
                    # Try to get memory from sysfs
                    for i in range(len(gpu_names)):
                        try:
                            with open(
                                f"/sys/class/drm/card{i}/device/mem_info_vram_total",
                                "r",
                            ) as f:
                                mem_bytes = int(f.read().strip())
                                gpu_memory[i] = mem_bytes / (1024**3)
                        except:
                            pass

                    return True, len(gpu_names), gpu_memory, gpu_names, gpu_vendors

        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.debug("rocm-smi not available")
        except Exception as e:
            logger.debug(f"Error detecting ROCm GPU: {e}")

        # Fallback to sysfs detection for AMD
        try:
            import glob

            amd_cards = []
            for vendor_file in glob.glob("/sys/class/drm/card*/device/vendor"):
                try:
                    with open(vendor_file, "r") as f:
                        vendor_id = f.read().strip()
                        if vendor_id == "0x1002":  # AMD vendor ID
                            card_path = vendor_file.replace("/vendor", "")
                            amd_cards.append(card_path)
                except:
                    continue

            if amd_cards:
                gpu_names = []
                gpu_memory = []
                gpu_vendors = []

                for card_path in amd_cards:
                    # Try to get device name
                    try:
                        with open(f"{card_path}/device/product_name", "r") as f:
                            name = f.read().strip()
                    except:
                        name = "AMD GPU"

                    # Try to get memory
                    try:
                        with open(f"{card_path}/device/mem_info_vram_total", "r") as f:
                            mem_bytes = int(f.read().strip())
                            mem_gb = mem_bytes / (1024**3)
                    except:
                        mem_gb = 0.0

                    gpu_names.append(name)
                    gpu_memory.append(mem_gb)
                    gpu_vendors.append("amd")

                return True, len(gpu_names), gpu_memory, gpu_names, gpu_vendors

        except Exception as e:
            logger.debug(f"Error detecting AMD GPU via sysfs: {e}")

        return False, 0, None, None, None

    def _detect_intel_gpu(
        self,
    ) -> Tuple[
        bool, int, Optional[List[float]], Optional[List[str]], Optional[List[str]]
    ]:
        """Detect Intel Arc/integrated GPUs via sysfs"""
        try:
            import glob

            intel_cards = []

            for vendor_file in glob.glob("/sys/class/drm/card*/device/vendor"):
                try:
                    with open(vendor_file, "r") as f:
                        vendor_id = f.read().strip()
                        if vendor_id == "0x8086":  # Intel vendor ID
                            card_path = vendor_file.replace("/vendor", "")
                            intel_cards.append(card_path)
                except:
                    continue

            if intel_cards:
                gpu_names = []
                gpu_memory = []
                gpu_vendors = []

                for card_path in intel_cards:
                    # Try to get device name
                    try:
                        with open(f"{card_path}/device/product_name", "r") as f:
                            name = f.read().strip()
                    except:
                        name = "Intel GPU"

                    # Intel integrated GPUs share system memory, estimate
                    # Discrete Arc GPUs have dedicated memory
                    try:
                        # Check for local memory (Arc)
                        with open(f"{card_path}/device/local_mem_info", "r") as f:
                            mem_bytes = int(f.read().strip())
                            mem_gb = mem_bytes / (1024**3)
                    except:
                        # Integrated GPU - use system memory as approximation
                        mem_gb = 0.0

                    gpu_names.append(name)
                    gpu_memory.append(mem_gb)
                    gpu_vendors.append("intel")

                return True, len(gpu_names), gpu_memory, gpu_names, gpu_vendors

        except Exception as e:
            logger.debug(f"Error detecting Intel GPU: {e}")

        return False, 0, None, None, None

    def _detect_gpu_via_pytorch(
        self,
    ) -> Tuple[
        bool, int, Optional[List[float]], Optional[List[str]], Optional[List[str]]
    ]:
        """Detect GPU using PyTorch (fallback method)"""
        try:
            import torch

            if not torch.cuda.is_available():
                return False, 0, None, None, None

            gpu_count = torch.cuda.device_count()
            gpu_memory = []
            gpu_names = []
            gpu_vendors = []

            for i in range(gpu_count):
                # Get device name
                name = torch.cuda.get_device_name(i)
                gpu_names.append(name)

                # Infer vendor from name
                name_lower = name.lower()
                if (
                    "nvidia" in name_lower
                    or "geforce" in name_lower
                    or "quadro" in name_lower
                    or "tesla" in name_lower
                ):
                    gpu_vendors.append("nvidia")
                elif "amd" in name_lower or "radeon" in name_lower:
                    gpu_vendors.append("amd")
                elif "intel" in name_lower or "arc" in name_lower:
                    gpu_vendors.append("intel")
                else:
                    gpu_vendors.append("unknown")

                # Get memory
                props = torch.cuda.get_device_properties(i)
                mem_gb = props.total_memory / (1024**3)
                gpu_memory.append(mem_gb)

            return True, gpu_count, gpu_memory, gpu_names, gpu_vendors

        except ImportError:
            logger.debug("PyTorch not available for GPU detection")
        except Exception as e:
            logger.warning(f"Error detecting GPU via PyTorch: {e}")

        return False, 0, None, None, None

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
    ) -> Optional[Any]:
        """
        Get the best model recommendation for the current system.

        Strategy: Best accuracy first, then efficiency.
        If multiple models have similar accuracy (within 0.05), prefer the more efficient one.

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

        # Use recommended if available, otherwise fall back to compatible
        candidates = recommended if recommended else compatible

        # Define tier-based performance defaults (higher = better accuracy)
        tier_performance = {
            "ultra_light": 0.70,  # tiny models
            "light": 0.80,  # small/distilled models
            "medium": 0.88,  # medium models
            "heavy": 0.95,  # large models
        }

        def get_model_performance(model) -> float:
            """Get performance score for a model, using actual data or tier-based inference."""
            perf_dict = getattr(model, "language_performance", {})

            # If we have language-specific performance, use it
            if language and language in perf_dict:
                return perf_dict[language]
            # If we have "all" language performance, use it
            elif "all" in perf_dict:
                return perf_dict["all"]
            # Otherwise, use tier-based default
            else:
                tier_str = (
                    model.tier.value
                    if hasattr(model.tier, "value")
                    else str(model.tier)
                )
                return tier_performance.get(tier_str, 0.75)

        def get_efficiency_score(model) -> float:
            """Calculate efficiency score (higher = more efficient)."""
            # Invert size to prefer smaller models: 1/size_mb
            return 1000.0 / max(model.size_mb, 1)  # Prevent division by zero

        # Sort candidates by: performance (desc), then efficiency (desc)
        # Use a tuple key: (-performance, -efficiency) so higher values sort first
        PERFORMANCE_THRESHOLD = (
            0.05  # Models within this threshold are "similar accuracy"
        )

        # First, sort by performance (highest first)
        candidates_with_perf = [(m, get_model_performance(m)) for m in candidates]
        candidates_with_perf.sort(
            key=lambda x: (-x[1], x[0].size_mb)
        )  # Performance desc, then size asc

        # Find the best model considering efficiency for similar-performance models
        best_model = None
        best_score = None

        if candidates_with_perf:
            # Group by performance tiers (within threshold)
            best_perf = candidates_with_perf[0][1]

            # Find all models with similar (within threshold) performance to the best
            similar_performance_models = [
                m
                for m, perf in candidates_with_perf
                if abs(perf - best_perf) <= PERFORMANCE_THRESHOLD
            ]

            # Among similar-performance models, pick the most efficient (smallest)
            if similar_performance_models:
                best_model = min(similar_performance_models, key=lambda m: m.size_mb)
            else:
                best_model = candidates_with_perf[0][0]

        if best_model:
            logger.info(
                f"Best model for system: {best_model.name} ({best_model.model_id})"
            )

        return best_model


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
