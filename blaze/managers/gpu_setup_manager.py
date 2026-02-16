"""GPU/CUDA setup and configuration manager"""
import os
import sys
import logging

logger = logging.getLogger(__name__)


class GPUSetupManager:
    """Manages GPU detection, CUDA library setup, and device configuration"""

    def __init__(self):
        self.gpu_available = False
        self.gpu_device_name = None
        self.cuda_lib_paths = []

    def setup(self):
        """
        Detect and configure CUDA libraries for GPU acceleration.
        If CUDA libraries are found but LD_LIBRARY_PATH is not set, restarts the process.

        Returns:
            bool: True if GPU is available and configured, False otherwise
        """
        # Check if we've already set up CUDA (to avoid infinite restart loop)
        if os.environ.get("SYLLABLAZE_CUDA_SETUP") == "1":
            return self._verify_cuda_setup()

        # Try to detect GPU and configure CUDA
        return self._detect_and_configure_cuda()

    def _verify_cuda_setup(self):
        """Verify that CUDA setup was successful after restart"""
        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        logger.info(
            f"✓ Running with CUDA libraries pre-configured (LD_LIBRARY_PATH has {len(ld_path)} chars)"
        )

        # Verify CUDA libraries are in the path
        if "nvidia" in ld_path:
            logger.info("✓ NVIDIA CUDA libraries are in LD_LIBRARY_PATH")
        else:
            logger.warning(
                "⚠ NVIDIA libraries not found in LD_LIBRARY_PATH - GPU may not work"
            )

        # Try to detect GPU name for user message
        self._detect_gpu_name()
        self._print_gpu_status(available=True)
        self.gpu_available = True
        return True

    def _detect_and_configure_cuda(self):
        """Detect GPU and configure CUDA libraries"""
        try:
            # First check if CUDA is available via torch
            if self._check_torch_cuda():
                logger.info(f"✓ CUDA available via PyTorch: {self.gpu_device_name}")

            # Try to find CUDA libraries in the pipx venv
            self._find_cuda_libraries()

            if self.cuda_lib_paths:
                # Check if LD_LIBRARY_PATH already contains our CUDA paths
                if self._should_restart_with_cuda():
                    self._restart_with_cuda_environment()
                    # execve never returns, but just in case:
                    sys.exit(0)

                logger.info("✓ CUDA libraries configured for GPU acceleration")
                self._print_gpu_status(available=True)
                self.gpu_available = True
                return True
            else:
                logger.info("✗ No CUDA libraries found in expected locations")
                if not self.gpu_device_name:
                    self._print_gpu_status(available=False)
                return False

        except Exception as e:
            logger.warning(f"Error setting up CUDA: {e}")
            print(f"⚠️  Could not configure GPU: {e}")
            print("   Falling back to CPU mode")
            return False

    def _check_torch_cuda(self):
        """Check if CUDA is available via PyTorch"""
        try:
            import torch

            if torch.cuda.is_available():
                self.gpu_device_name = torch.cuda.get_device_name(0)
                return True
            else:
                logger.info("✗ CUDA not available via PyTorch - will check for CUDA libraries")
                return False
        except ImportError:
            logger.info("PyTorch not installed - checking for CUDA libraries directly")
            return False

    def _detect_gpu_name(self):
        """Try to detect GPU name for logging"""
        if self.gpu_device_name:
            return

        try:
            import torch

            if torch.cuda.is_available():
                self.gpu_device_name = torch.cuda.get_device_name(0)
        except ImportError:
            pass

    def _find_cuda_libraries(self):
        """Search for NVIDIA CUDA libraries in the pipx venv"""
        venv_path = os.path.expanduser("~/.local/share/pipx/venvs/syllablaze")
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        site_packages = os.path.join(
            venv_path, f"lib/python{python_version}/site-packages"
        )

        potential_paths = [
            os.path.join(site_packages, "nvidia/cublas/lib"),
            os.path.join(site_packages, "nvidia/cudnn/lib"),
            os.path.join(site_packages, "nvidia/cuda_runtime/lib"),
        ]

        self.cuda_lib_paths = []
        for path in potential_paths:
            if os.path.exists(path):
                self.cuda_lib_paths.append(path)
                logger.info(
                    f"✓ Found CUDA library: {os.path.basename(os.path.dirname(path))}"
                )

    def _should_restart_with_cuda(self):
        """Check if we need to restart the process with CUDA paths"""
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        return not any(path in current_ld_path for path in self.cuda_lib_paths)

    def _restart_with_cuda_environment(self):
        """Restart the process with CUDA library paths in LD_LIBRARY_PATH"""
        logger.info("🔄 Restarting with CUDA library paths...")
        print("🔄 Detected GPU, restarting with CUDA support...")

        # Set up environment for restart
        new_env = os.environ.copy()
        current_ld_path = new_env.get("LD_LIBRARY_PATH", "")
        cuda_path_str = ":".join(self.cuda_lib_paths)

        if current_ld_path:
            new_env["LD_LIBRARY_PATH"] = f"{cuda_path_str}:{current_ld_path}"
        else:
            new_env["LD_LIBRARY_PATH"] = cuda_path_str
        new_env["SYLLABLAZE_CUDA_SETUP"] = "1"

        # Restart the process with the new environment
        args = [sys.executable] + sys.argv
        logger.info(f"Restarting with args: {args}")
        os.execve(sys.executable, args, new_env)

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
