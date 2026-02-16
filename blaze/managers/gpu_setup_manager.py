"""GPU/CUDA setup and configuration manager"""
import os
import sys
import logging
import ctypes
import glob

logger = logging.getLogger(__name__)


class GPUSetupManager:
    """Manages GPU detection, CUDA library setup, and device configuration"""

    def __init__(self):
        self.gpu_available = False
        self.gpu_device_name = None
        self.cuda_lib_paths = []

    def setup(self):
        """
        Detect GPU availability via PyTorch and CTranslate2.
        No restart needed - modern libraries bundle CUDA internally.

        Returns:
            bool: True if GPU is available, False otherwise
        """
        return self._detect_and_configure_cuda()

    def _detect_and_configure_cuda(self):
        """Detect GPU and configure CUDA library paths if needed"""
        try:
            # Check PyTorch CUDA availability
            pytorch_available = self._check_torch_cuda()

            # Check CTranslate2 CUDA availability
            ctranslate2_available = self._check_ctranslate2_cuda()

            if pytorch_available or ctranslate2_available:
                # Configure CUDA library paths for CTranslate2
                self._configure_cuda_library_paths()

                logger.info("✓ GPU acceleration available")
                self._print_gpu_status(available=True)
                self.gpu_available = True
                return True
            else:
                logger.info("✗ No GPU acceleration available")
                self._print_gpu_status(available=False)
                return False

        except Exception as e:
            logger.warning(f"Error during GPU detection: {e}")
            print(f"⚠️  Could not detect GPU: {e}")
            print("   Falling back to CPU mode")
            return False

    def _check_torch_cuda(self):
        """Check if CUDA is available via PyTorch"""
        try:
            import torch

            if torch.cuda.is_available():
                self.gpu_device_name = torch.cuda.get_device_name(0)
                logger.info(f"✓ CUDA available via PyTorch: {self.gpu_device_name}")
                return True
            else:
                logger.info("✗ CUDA not available via PyTorch")
                return False
        except ImportError:
            logger.info("PyTorch not installed")
            return False

    def _check_ctranslate2_cuda(self):
        """Check if CTranslate2 has CUDA support"""
        try:
            import ctranslate2

            cuda_devices = ctranslate2.get_cuda_device_count()
            if cuda_devices > 0:
                logger.info(f"✓ CTranslate2 reports {cuda_devices} CUDA device(s)")
                if not self.gpu_device_name:
                    self.gpu_device_name = "CUDA Device (via CTranslate2)"
                return True
            else:
                logger.info("✗ CTranslate2 reports no CUDA devices")
                return False
        except ImportError:
            logger.info("CTranslate2 not installed")
            return False
        except Exception as e:
            logger.warning(f"Error checking CTranslate2 CUDA: {e}")
            return False

    def _configure_cuda_library_paths(self):
        """Preload NVIDIA CUDA libraries so CTranslate2 can find them"""
        venv_path = os.path.expanduser("~/.local/share/pipx/venvs/syllablaze")
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(venv_path, f"lib/python{python_version}/site-packages")

        # Search for NVIDIA CUDA library packages
        nvidia_dirs = ["nvidia/cublas/lib", "nvidia/cudnn/lib", "nvidia/cuda_runtime/lib"]
        cuda_paths = []

        for nvidia_dir in nvidia_dirs:
            lib_path = os.path.join(site_packages, nvidia_dir)
            if os.path.exists(lib_path):
                cuda_paths.append(lib_path)
                logger.info(f"✓ Found CUDA library: {nvidia_dir}")

        if cuda_paths:
            # Preload critical CUDA libraries using ctypes
            # This must happen before CTranslate2 is imported
            preloaded = 0
            for lib_path in cuda_paths:
                # Find all .so files in this directory
                so_files = glob.glob(os.path.join(lib_path, "*.so.*"))
                for so_file in so_files:
                    try:
                        ctypes.CDLL(so_file, mode=ctypes.RTLD_GLOBAL)
                        preloaded += 1
                        logger.debug(f"  Preloaded: {os.path.basename(so_file)}")
                    except Exception as e:
                        logger.debug(f"  Could not preload {os.path.basename(so_file)}: {e}")

            logger.info(f"✓ Preloaded {preloaded} CUDA libraries from {len(cuda_paths)} paths")
            self.cuda_lib_paths = cuda_paths
        else:
            logger.warning("⚠ No NVIDIA CUDA library packages found in venv")
            logger.warning("  Install with: pipx inject syllablaze nvidia-cublas-cu12 nvidia-cudnn-cu12")

    def _print_gpu_status(self, available):
        """Print user-friendly GPU status message"""
        if available:
            if self.gpu_device_name:
                print(f"🚀 GPU acceleration enabled using: {self.gpu_device_name}")
            else:
                print("🚀 GPU acceleration enabled with CUDA libraries")
        else:
            print("⚠️  No GPU detected. Running in CPU mode (slower).")
            print("   To enable GPU: Install CUDA-enabled PyTorch and NVIDIA libraries")

    def configure_settings(self, settings):
        """
        Configure device and compute_type settings based on GPU availability

        Args:
            settings: Settings instance to update
        """
        if self.gpu_available:
            settings.set("device", "cuda")
            settings.set("compute_type", "float16")  # Better GPU performance
            logger.info("Settings configured for GPU: device=cuda, compute_type=float16")
        else:
            settings.set("device", "cpu")
            settings.set("compute_type", "float32")
            logger.info("Settings configured for CPU: device=cpu, compute_type=float32")

    def is_gpu_available(self):
        """Return whether GPU is available and configured"""
        return self.gpu_available

    def get_device_name(self):
        """Return human-readable GPU device name or None"""
        return self.gpu_device_name
