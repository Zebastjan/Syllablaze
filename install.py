#!/usr/bin/env python3

# Syllablaze Installation Script
#
# Standard installation (stable):
#   python3 install.py
#
# Development installation (parallel, editable):
#   pipx install -e . --force --system-site-packages --suffix=-dev
#   Creates 'syllablaze-dev' command alongside 'syllablaze'
#   Useful for testing new features (e.g., Kirigami UI) without disrupting stable version

import os
import shutil
import sys
import subprocess
import warnings
import threading
import time
import itertools

# Add the current directory to the path so we can import from blaze
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_system_dependencies():
    """Check if required system dependencies are installed"""
    dependencies = ["pipx"]
    missing = []
    
    for dep in dependencies:
        try:
            subprocess.check_call(["which", dep], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            missing.append(dep)
    
    if missing:
        print(f"Missing system dependencies: {', '.join(missing)}")
        print("Please install them using:")
        if os.path.exists("/etc/debian_version"):  # Ubuntu/Debian
            if "pipx" in missing:
                print("sudo apt install -y python3-pipx")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            if "pipx" in missing:
                print("sudo dnf install -y pipx")
        else:
            print(f"Please install: {' '.join(missing)}")
        return False
    return True

def print_stage(stage_num, total_stages, stage_name):
    """Print a formatted installation stage"""
    print(f"\n[{stage_num}/{total_stages}] {stage_name}")

def install_with_pipx(skip_whisper=False):
    """Install the application using pipx"""
    # Import version from constants
    from blaze.constants import APP_VERSION

    # Define total number of installation stages
    total_stages = 6  # Dependencies check, setup creation, pipx install, verification, desktop integration, completion

    print_stage(1, total_stages, "Checking dependencies and preparing installation")
    try:
        # Process requirements.txt
        with open("requirements.txt", "r") as f:
            requirements = f.read().splitlines()

        # Filter out empty lines and comments
        requirements = [req for req in requirements if req and not req.startswith('#')]

        # Remove openai-whisper if skip_whisper is True
        if skip_whisper:
            requirements = [req for req in requirements if "openai-whisper" not in req]
            print("NOTE: Skipping openai-whisper as requested. You will need to install it manually later.")

        # Display requirements that will be installed
        print("Packages that will be installed:")
        for i, req in enumerate(requirements, 1):
            print(f"  {i}. {req}")

        # Create setup.py file for pipx installation
        print_stage(2, total_stages, "Creating setup configuration")
        with open("setup.py", "w") as f:
            f.write(f"""
from setuptools import setup, find_packages
import os
import sys

# Read requirements.txt and filter out empty lines/comments
with open("requirements.txt") as req_file:
    requirements = [
        line.strip()
        for line in req_file
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="syllablaze",
    version="{APP_VERSION}",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={{
        "console_scripts": [
            "syllablaze=blaze.main:main",
        ],
    }},
)
""")
        
        # Install with pipx
        print_stage(3, total_stages, "Installing packages with pipx")
        print("This may take a few minutes. Please be patient.")
        
        # Show what packages will be installed in order
        print("  The following packages will be installed:")
        for i, package in enumerate(requirements, 1):
            print(f"    {i}/{len(requirements)} - {package}")
        
        print("\n  Starting installation...")
        
        # Create a subprocess with proper output handling
        try:
            process = subprocess.Popen(
                ["pipx", "install", ".", "--force", "--verbose", "--system-site-packages"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Stream output in real-time with progress tracking
            print("\n  Installation progress:")
            current_package = None
            pip_install_started = False

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break

                line = output.strip()

                # Skip empty lines
                if not line:
                    continue

                # Show all output for transparency
                print(f"  {line}")

                # Track installation progress markers
                if "Collecting" in line or "Downloading" in line:
                    # Highlight package downloads
                    if current_package not in line:
                        for package in requirements:
                            if package in line:
                                current_package = package
                                print(f"  → Installing {package}...")
                                break

                # Show successful installation message
                if "Successfully installed" in line:
                    print("  ✓ Installation packages ready")

            # Check return code
            return_code = process.poll()
            if return_code != 0:
                # Show error output
                error_output = process.stderr.read()
                if error_output:
                    print(f"\n  [ERROR] Installation failed with errors:")
                    print(f"  {error_output}")
                raise subprocess.CalledProcessError(return_code, process.args)
        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] Installation failed: {e}")
            return False

        # Installation successful
        print("\n  [SUCCESS] Installation process completed successfully.")

        # Close stdout to prevent resource leaks
        process.stdout.close()

        print_stage(4, total_stages, "Verifying installation")
        # Verification happens in verify_installation() function
        
        print_stage(5, total_stages, "Installation completed")
        return True
    except Exception as e:
        print(f"Failed to install application: {e}")
        return False

def suppress_alsa_errors():
    """Suppress ALSA error messages with better error handling"""
    try:
        import ctypes
        # Load ALSA error handler
        ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                            ctypes.c_char_p, ctypes.c_int,
                                            ctypes.c_char_p)
    
        def py_error_handler(filename, line, function, err, fmt):
            pass
    
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    
        # Try standard library path first
        try:
            asound = ctypes.cdll.LoadLibrary('libasound.so.2')
            asound.snd_lib_error_set_handler(c_error_handler)
            return True
        except OSError:
            # Try alternative paths common on Ubuntu
            alt_paths = [
                '/usr/lib/x86_64-linux-gnu/libasound.so.2',
                '/usr/lib/libasound.so.2'
            ]
            for path in alt_paths:
                try:
                    asound = ctypes.cdll.LoadLibrary(path)
                    asound.snd_lib_error_set_handler(c_error_handler)
                    return True
                except OSError:
                    continue
            warnings.warn("Failed to suppress ALSA warnings", RuntimeWarning)
            return False
    except Exception:
        warnings.warn("Failed to suppress ALSA warnings", RuntimeWarning)
        return False

def install_desktop_integration():
    """Install desktop integration files for KDE"""
    try:
        # Create necessary directories
        app_dir = os.path.expanduser("~/.local/share/applications")
        icon_dir = os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps")
        
        # Create directories if they don't exist
        os.makedirs(app_dir, exist_ok=True)
        os.makedirs(icon_dir, exist_ok=True)
        
        # Copy desktop file from resources directory
        desktop_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "org.kde.syllablaze.desktop")
        desktop_dst = os.path.join(app_dir, "org.kde.syllablaze.desktop")
        shutil.copy2(desktop_src, desktop_dst)
        
        # Set proper permissions for desktop file
        os.chmod(desktop_dst, 0o644)  # rw-r--r--
        
        # Copy icon from resources directory (using SVG for better scaling)
        icon_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "syllablaze.svg")
        icon_dst = os.path.join(icon_dir, "syllablaze.svg")
        shutil.copy2(icon_src, icon_dst)

        # Also copy icon to applications directory for better compatibility
        icon_app_dst = os.path.join(app_dir, "syllablaze.svg")
        shutil.copy2(icon_src, icon_app_dst)

        # For backward compatibility, also install as PNG name (some systems may look for it)
        icon_dst_png = os.path.join(icon_dir, "syllablaze.png")
        shutil.copy2(icon_src, icon_dst_png)
        icon_app_dst_png = os.path.join(app_dir, "syllablaze.png")
        shutil.copy2(icon_src, icon_app_dst_png)
        
        # Make run script executable (now in blaze/ directory)
        run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blaze", "run-syllablaze.sh")
        os.chmod(run_script, 0o755)  # rwxr-xr-x

        # Install D-Bus toggle script for KDE shortcuts
        toggle_script_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blaze", "toggle-syllablaze.sh")
        toggle_script_dst = os.path.expanduser("~/.local/bin/toggle-syllablaze.sh")
        shutil.copy2(toggle_script_src, toggle_script_dst)
        os.chmod(toggle_script_dst, 0o755)  # rwxr-xr-x
        print(f" Toggle script: {toggle_script_dst}")
        
        # Update desktop database
        try:
            subprocess.run(["update-desktop-database", app_dir], check=False)
        except OSError:
            pass  # Not critical if this fails
            
        # Force KDE to refresh its menu cache
        try:
            subprocess.run(["kbuildsycoca5"], check=False)
        except OSError:
            try:
                subprocess.run(["kbuildsycoca6"], check=False)  # For newer KDE versions
            except OSError:
                pass  # Not critical if this fails
            
        print("  [SUCCESS] Desktop integration files installed successfully")
        print(f"    Desktop file: {desktop_dst}")
        print(f"    Icon: {icon_dst} (and .png fallback)")
        print("    KDE menu cache refreshed")
        return True
    except Exception as e:
        print(f"  [WARNING] Failed to install desktop integration: {e}")
        return False

def verify_installation():
    """Verify that the application was installed correctly"""
    # This function is called after stage 4 is displayed in install_with_pipx
    
    # Check pipx installation
    try:
        print("  Checking pipx installation...")
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "syllablaze" in result.stdout:
            print("  [SUCCESS] ✓ Syllablaze successfully installed with pipx")
            # Extract and display the installation path
            for line in result.stdout.splitlines():
                if "syllablaze" in line:
                    print(f"    {line.strip()}")
            return True
        else:
            print("  [WARNING] ✗ Syllablaze not found in pipx installed applications")
            return False
    except subprocess.CalledProcessError:
        print("  [ERROR] ✗ Failed to verify pipx installation")
        return False

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    parser = argparse.ArgumentParser(description="Install Syllablaze")
    parser.add_argument("--skip-whisper", action="store_true", help="Skip installing the openai-whisper package")
    parser.add_argument("--force-reinstall", action="store_true",
                       help="Uninstall existing installation and reinstall (preserves settings)")
    return parser.parse_args()

def check_if_already_installed(force_reinstall=False):
    """Check if Syllablaze is already installed with pipx"""
    try:
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "syllablaze" in result.stdout:
            if force_reinstall:
                print("[INFO] Syllablaze is already installed. Reinstalling...")
                subprocess.run(["pipx", "uninstall", "syllablaze"], check=True)
                return False  # Allow installation to proceed
            else:
                # Interactive prompt
                print("[INFO] Syllablaze is already installed.")
                response = input("Reinstall? (y/n): ").strip().lower()
                if response == 'y':
                    print("Uninstalling existing installation...")
                    subprocess.run(["pipx", "uninstall", "syllablaze"], check=True)
                    return False  # Allow installation to proceed
                else:
                    print("Installation cancelled.")
                    return True  # Block installation
        return False
    except subprocess.CalledProcessError:
        return False

def check_gpu_support():
    """Check if CUDA is available for GPU acceleration"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
    except Exception:
        return False

def run_installation(skip_whisper=False, force_reinstall=False):
    """Run the complete installation process with stages"""
    # Check if already installed
    if check_if_already_installed(force_reinstall=force_reinstall):
        return False
        
    # Check system dependencies
    if not check_system_dependencies():
        print("Missing system dependencies. Please install them and try again.")
        return False
    
    # Check for GPU support
    has_gpu = check_gpu_support()
    if has_gpu:
        print("GPU support detected. Installing CUDA dependencies...")
        # Inform user about CUDA requirements
        print("Note: For optimal performance with Faster Whisper on GPU, ensure you have:")
        print("- CUDA 12 with cuBLAS")
        print("- cuDNN 9 for CUDA 12")
        print("These can be installed separately if not already present.")
    else:
        print("No GPU detected. Configuring for CPU-only operation.")
    
    # Install with pipx (includes stages 1-3)
    if not install_with_pipx(skip_whisper=skip_whisper):
        print("Failed to install application with pipx. Installation aborted.")
        return False
    
    # Verify installation (stage 4 is displayed in install_with_pipx)
    verify_installation()
    
    # Install desktop integration
    print_stage(5, 6, "Installing desktop integration")
    install_desktop_integration()
    
    # Final message
    print_stage(6, 6, "Installation completed")
    print("\nYou can now run Syllablaze in two ways:")
    print("  1. Type 'syllablaze' in the terminal")
    print("  2. Find it in your application menu under 'Utilities' or 'AudioVideo'")
    
    # Additional GPU-specific instructions
    if has_gpu:
        print("\nFor GPU acceleration with Faster Whisper, you may need to install:")
        print("  pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*")
    
    return True

if __name__ == "__main__":
    # Suppress ALSA errors
    suppress_alsa_errors()
    
    # Parse arguments
    args = parse_arguments()
    
    # Run installation
    try:
        if not run_installation(skip_whisper=args.skip_whisper,
                               force_reinstall=args.force_reinstall):
            sys.exit(1)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInstallation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Installation failed with error: {e}")
        sys.exit(1)
