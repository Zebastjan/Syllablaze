"""
Dependency Manager for Optional Backends

Handles installation of backend dependencies when users want to use
optional backends like Liquid, Granite, or Qwen.
"""

import subprocess
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


# Dependencies required by each backend
BACKEND_DEPENDENCIES = {
    "liquid": {
        "packages": ["liquid-audio", "torchaudio"],
        "optional": ["flash-attn"],
        "description": "Liquid AI LFM2.5-Audio",
        "size_estimate": "~3GB download",
        "install_command": "pip install liquid-audio torchaudio",
    },
    "granite": {
        "packages": ["transformers>=4.40.0", "torchaudio", "peft", "soundfile"],
        "optional": [],
        "description": "IBM Granite Speech",
        "size_estimate": "~4GB download",
        "install_command": "pip install transformers>=4.40.0 torchaudio peft soundfile",
    },
    "qwen": {
        "packages": ["huggingface-hub"],  # For model downloads
        "optional": [],
        "description": "Qwen2.5-Omni Multimodal (10k+ languages)",
        "size_estimate": "~2-8GB models + llama.cpp binary",
        "install_command": "# Requires manual llama.cpp compilation - see instructions",
        "requires_binary": "llama-mtmd-cli",
        "binary_install_url": "https://github.com/ggml-org/llama.cpp",
    },
}


class DependencyManager:
    """Manages installation of optional backend dependencies"""

    @classmethod
    def get_backend_info(cls, backend: str) -> Optional[dict]:
        """Get information about a backend's dependencies"""
        return BACKEND_DEPENDENCIES.get(backend)

    @classmethod
    def is_backend_available(cls, backend: str) -> bool:
        """Check if a backend's dependencies are installed"""
        try:
            if backend == "liquid":
                import liquid_audio
                import torchaudio
                return True
            elif backend == "granite":
                import transformers
                import torchaudio
                import peft
                import soundfile
                return True
            elif backend == "qwen":
                # Check for both Python deps AND binary
                import shutil
                import huggingface_hub
                # Qwen requires llama-mtmd-cli binary to actually work
                # But we check Python deps are installed too
                has_binary = shutil.which("llama-mtmd-cli") is not None
                # Return True if binary is present (Python deps checked by import above)
                return has_binary
        except ImportError:
            pass
        return False

    @classmethod
    def get_backend_status(cls, backend: str) -> dict:
        """
        Get detailed status of a backend's dependencies.

        Returns:
            dict with keys:
                - available: bool - fully ready to use
                - python_deps_installed: bool - Python packages installed
                - binary_installed: bool - Required binary installed (if applicable)
                - missing_binary: str - Name of missing binary (if applicable)
        """
        status = {
            "available": False,
            "python_deps_installed": False,
            "binary_installed": True,  # Default True for backends without binary
            "missing_binary": None,
        }

        try:
            if backend == "liquid":
                import liquid_audio
                import torchaudio
                status["python_deps_installed"] = True
                status["available"] = True
            elif backend == "granite":
                import transformers
                import torchaudio
                import peft
                import soundfile
                status["python_deps_installed"] = True
                status["available"] = True
            elif backend == "qwen":
                import shutil
                import huggingface_hub
                status["python_deps_installed"] = True
                status["binary_installed"] = shutil.which("llama-mtmd-cli") is not None
                status["missing_binary"] = "llama-mtmd-cli" if not status["binary_installed"] else None
                status["available"] = status["binary_installed"]
        except ImportError:
            pass

        return status

    @classmethod
    def install_backend(
        cls,
        backend: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        include_optional: bool = False,
    ) -> bool:
        """
        Install dependencies for a backend.

        Args:
            backend: Backend name (liquid, granite, qwen)
            progress_callback: Optional callback(message, progress_percent)
            include_optional: Whether to install optional dependencies

        Returns:
            True if installation succeeded
        """
        info = BACKEND_DEPENDENCIES.get(backend)
        if not info:
            logger.error(f"Unknown backend: {backend}")
            return False

        packages = info["packages"].copy()
        if include_optional and info["optional"]:
            packages.extend(info["optional"])

        logger.info(f"Installing dependencies for {backend}: {packages}")

        if progress_callback:
            progress_callback(f"Installing {info['description']}...", 0)

        try:
            # Build pip install command
            cmd = [sys.executable, "-m", "pip", "install"] + packages

            logger.info(f"Running: {' '.join(cmd)}")

            # Run pip install
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Stream output
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"pip: {line}")
                    if progress_callback:
                        # Simple progress based on keywords
                        if "Collecting" in line:
                            progress_callback(f"Downloading packages...", 25)
                        elif "Installing" in line or "Building" in line:
                            progress_callback(f"Installing packages...", 50)
                        elif "Successfully" in line:
                            progress_callback(f"Installation complete!", 100)

            process.wait()

            if process.returncode == 0:
                logger.info(f"Successfully installed {backend} dependencies")
                if progress_callback:
                    progress_callback(
                        f"{info['description']} installed successfully!", 100
                    )
                return True
            else:
                logger.error(
                    f"Installation failed with return code {process.returncode}"
                )
                return False

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            if progress_callback:
                progress_callback(f"Installation failed: {e}", 0)
            return False

    @classmethod
    def get_install_command(cls, backend: str) -> str:
        """Get the pip install command for a backend"""
        info = BACKEND_DEPENDENCIES.get(backend)
        if not info:
            return ""

        packages = " ".join(info["packages"])
        return f"pip install {packages}"

    @classmethod
    def get_shared_dependencies(cls, package: str) -> List[str]:
        """
        Get list of backends that depend on a specific package.

        Args:
            package: Package name (e.g., 'torchaudio')

        Returns:
            List of backend names that require this package
        """
        backends = []
        for backend, info in BACKEND_DEPENDENCIES.items():
            # Check both required and optional packages
            all_packages = info["packages"] + info.get("optional", [])
            # Handle version specifiers (e.g., 'transformers>=4.40.0')
            package_base = package.split(">=")[0].split("==")[0].split("<")[0].split(">")[0]
            for pkg in all_packages:
                pkg_base = pkg.split(">=")[0].split("==")[0].split("<")[0].split(">")[0]
                if pkg_base == package_base:
                    backends.append(backend)
                    break
        return backends

    @classmethod
    def can_uninstall_package(
        cls,
        package: str,
        backend: str,
        backends_being_uninstalled: Optional[List[str]] = None,
    ) -> tuple[bool, List[str]]:
        """
        Check if a package can be safely uninstalled.

        Args:
            package: Package name
            backend: Backend requesting uninstall
            backends_being_uninstalled: List of backends currently being uninstalled

        Returns:
            (can_uninstall, other_backends_using_it)
            can_uninstall is False if other installed backends need it
        """
        if backends_being_uninstalled is None:
            backends_being_uninstalled = []

        dependent_backends = cls.get_shared_dependencies(package)
        # Remove the requesting backend AND any being uninstalled
        other_backends = [
            b for b in dependent_backends
            if b != backend and b not in backends_being_uninstalled
        ]

        # Check if any other backend is actually installed
        installed_others = [b for b in other_backends if cls.is_backend_available(b)]

        can_uninstall = len(installed_others) == 0
        return can_uninstall, installed_others

    @classmethod
    def uninstall_backend(
        cls,
        backend: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        force: bool = False,
    ) -> dict:
        """
        Uninstall dependencies for a backend.

        Args:
            backend: Backend name (liquid, granite, qwen)
            progress_callback: Optional callback(message, progress_percent)
            force: If True, uninstall even shared dependencies (dangerous!)

        Returns:
            dict with:
                - success: bool
                - uninstalled: list of packages uninstalled
                - skipped: list of packages skipped (shared with other backends)
                - warnings: list of warning messages
        """
        info = BACKEND_DEPENDENCIES.get(backend)
        if not info:
            logger.error(f"Unknown backend: {backend}")
            return {"success": False, "error": "Unknown backend"}

        packages = info["packages"].copy()
        if info.get("optional"):
            packages.extend(info["optional"])

        logger.info(f"Uninstalling dependencies for {backend}: {packages}")

        if progress_callback:
            progress_callback(f"Analyzing {info['description']} dependencies...", 10)

        uninstalled = []
        skipped = []
        warnings = []

        # Check each package for shared dependencies
        # Pass current backend as being uninstalled to prevent circular dependency bug
        for pkg in packages:
            can_uninstall, other_backends = cls.can_uninstall_package(
                pkg, backend, backends_being_uninstalled=[backend]
            )

            if not can_uninstall and not force:
                skipped.append(pkg)
                warning = f"Skipped {pkg} (needed by: {', '.join(other_backends)})"
                warnings.append(warning)
                logger.warning(warning)
                continue

            # Safe to uninstall (or forced)
            try:
                if progress_callback:
                    progress_callback(f"Uninstalling {pkg}...", 30)

                cmd = [sys.executable, "-m", "pip", "uninstall", "-y", pkg]
                logger.info(f"Running: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode == 0:
                    uninstalled.append(pkg)
                    logger.info(f"Successfully uninstalled {pkg}")
                else:
                    logger.warning(f"Failed to uninstall {pkg}: {result.stderr}")
                    warnings.append(f"Failed to uninstall {pkg}")

            except Exception as e:
                logger.error(f"Error uninstalling {pkg}: {e}")
                warnings.append(f"Error uninstalling {pkg}: {e}")

        if progress_callback:
            if uninstalled:
                progress_callback(f"Uninstalled {len(uninstalled)} package(s)", 100)
            elif skipped:
                progress_callback("No packages uninstalled (all shared with other backends)", 100)
            else:
                progress_callback("Uninstall completed", 100)

        # Consider successful if:
        # 1. At least one package was uninstalled, OR
        # 2. No packages to uninstall (backend had no deps), OR
        # 3. All packages were skipped (shared deps = partial success)
        # Only fail if there were packages but none were uninstalled and none were skipped
        success = (
            len(uninstalled) > 0
            or len(packages) == 0
            or (len(skipped) > 0 and len(packages) == len(skipped) + len(uninstalled))
        )

        return {
            "success": success,
            "uninstalled": uninstalled,
            "skipped": skipped,
            "warnings": warnings,
        }


def install_liquid_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """Convenience function to install Liquid backend"""
    return DependencyManager.install_backend("liquid", progress_callback)


def install_granite_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """Convenience function to install Granite backend"""
    return DependencyManager.install_backend("granite", progress_callback)


def install_qwen_binary(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """
    Automated installation of llama-mtmd-cli binary.

    This function runs the shell script that:
    - Clones llama.cpp repository
    - Compiles llama-mtmd-cli binary (5-15 minutes)
    - Installs to ~/.local/bin (no sudo required)
    - Verifies binary works

    Args:
        progress_callback: Optional callback(message, progress_percent)

    Returns:
        True if installation succeeded
    """
    logger.info("Starting automated llama-mtmd-cli installation")

    # Locate installation script
    script_path = Path(__file__).parent.parent / "scripts" / "install_llama_mtmd_cli.sh"
    if not script_path.exists():
        logger.error(f"Installation script not found: {script_path}")
        if progress_callback:
            progress_callback(f"Installation script not found: {script_path}", 0)
        return False

    # Installation directory (no sudo needed)
    install_dir = Path.home() / ".local" / "bin"

    if progress_callback:
        progress_callback("Starting binary compilation (5-15 minutes)...", 0)

    try:
        # Run installation script
        process = subprocess.Popen(
            [str(script_path), str(install_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Parse script output for progress/errors
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            logger.info(f"install_script: {line}")

            if line.startswith("PROGRESS:"):
                # Parse: PROGRESS:percent:message
                try:
                    _, percent_str, message = line.split(":", 2)
                    percent = int(percent_str)
                    if progress_callback:
                        progress_callback(message, percent)
                except ValueError as e:
                    logger.warning(f"Failed to parse progress line: {line} ({e})")

            elif line.startswith("ERROR:"):
                # Parse: ERROR:message
                error_msg = line.split(":", 1)[1] if ":" in line else line
                logger.error(f"Build error: {error_msg}")
                if progress_callback:
                    progress_callback(f"Build failed: {error_msg}", 0)

        # Wait for completion
        process.wait()

        if process.returncode == 0:
            logger.info("llama-mtmd-cli installed successfully")
            if progress_callback:
                progress_callback("Binary installed successfully!", 100)
            return True
        else:
            logger.error(f"Installation failed with return code {process.returncode}")
            if progress_callback:
                progress_callback(f"Installation failed (exit code {process.returncode})", 0)
            return False

    except Exception as e:
        logger.error(f"Binary installation failed: {e}")
        if progress_callback:
            progress_callback(f"Installation error: {e}", 0)
        return False


def install_qwen_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
    auto_install_binary: bool = False,
) -> bool:
    """
    Install Qwen backend dependencies.

    Args:
        progress_callback: Optional callback(message, progress_percent)
        auto_install_binary: If True, automatically compile/install llama-mtmd-cli

    Returns:
        True if installation succeeded
    """
    # Step 1: Install Python dependencies (0-10%)
    if progress_callback:
        progress_callback("Installing Python dependencies...", 0)

    success = DependencyManager.install_backend("qwen", progress_callback)
    if not success:
        return False

    # Step 2: Check if binary already exists
    if shutil.which("llama-mtmd-cli"):
        logger.info("llama-mtmd-cli already available")
        if progress_callback:
            progress_callback("Qwen ready! (llama-mtmd-cli found)", 100)
        return True

    # Step 3: Auto-install binary if requested
    if auto_install_binary:
        logger.info("Binary not found, starting automated installation")
        if progress_callback:
            progress_callback("Python dependencies installed, compiling binary...", 10)

        # Map binary installation progress (0-100%) to overall (10-100%)
        def binary_progress(message: str, percent: int):
            overall_percent = 10 + int(percent * 0.9)
            if progress_callback:
                progress_callback(message, overall_percent)

        return install_qwen_binary(binary_progress)

    # Step 4: Binary not found, provide manual instructions
    logger.warning("llama-mtmd-cli not found - manual installation required")

    if progress_callback:
        instructions = """
Qwen2.5-Omni requires llama-mtmd-cli:

1. Clone llama.cpp:
   cd ~ && git clone https://github.com/ggml-org/llama.cpp.git

2. Configure with CMake (CUDA enabled):
   cd llama.cpp && mkdir -p build && cd build
   cmake .. -DGGML_CUDA=ON -DLLAMA_BUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release

3. Compile multimodal CLI:
   cmake --build . --target llama-mtmd-cli -j$(nproc)

4. Install binary:
   sudo cp bin/llama-mtmd-cli /usr/local/bin/
   # OR: mkdir -p ~/.local/bin && cp bin/llama-mtmd-cli ~/.local/bin/

5. Verify: llama-mtmd-cli --help

See: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
"""
        progress_callback(instructions, 100)

    return True


def uninstall_liquid_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """Convenience function to uninstall Liquid backend"""
    return DependencyManager.uninstall_backend("liquid", progress_callback)


def uninstall_granite_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """Convenience function to uninstall Granite backend"""
    return DependencyManager.uninstall_backend("granite", progress_callback)


def uninstall_qwen_binary(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """
    Remove llama-mtmd-cli binary if installed in ~/.local/bin.

    Args:
        progress_callback: Optional callback(message, progress_percent)

    Returns:
        True if binary was removed or didn't exist
    """
    binary_path = Path.home() / ".local" / "bin" / "llama-mtmd-cli"

    if not binary_path.exists():
        logger.info("llama-mtmd-cli not found in ~/.local/bin")
        if progress_callback:
            progress_callback("Binary not found (already removed or never installed)", 100)
        return True

    try:
        if progress_callback:
            progress_callback(f"Removing {binary_path}...", 50)

        binary_path.unlink()
        logger.info(f"Removed llama-mtmd-cli binary: {binary_path}")

        if progress_callback:
            progress_callback("Binary removed successfully", 100)
        return True

    except Exception as e:
        logger.error(f"Failed to remove binary: {e}")
        if progress_callback:
            progress_callback(f"Failed to remove binary: {e}", 0)
        return False


def uninstall_qwen_backend(
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """
    Uninstall Qwen backend.

    This removes both Python dependencies and the llama-mtmd-cli binary
    (if installed in ~/.local/bin).

    Args:
        progress_callback: Optional callback(message, progress_percent)

    Returns:
        dict with uninstall results
    """
    # Uninstall Python dependencies first
    result = DependencyManager.uninstall_backend("qwen", progress_callback)

    # Also remove binary if present
    binary_removed = uninstall_qwen_binary(progress_callback)

    # Update result to include binary removal
    if binary_removed:
        if "uninstalled" not in result:
            result["uninstalled"] = []
        result["uninstalled"].append("llama-mtmd-cli (binary)")

    return result
