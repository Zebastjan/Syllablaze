#!/usr/bin/env python3

import os
import shutil
from pathlib import Path
import sys
import subprocess
import warnings

# Add the current directory to the path so we can import from blaze
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from blaze.constants import APP_VERSION

def check_system_dependencies():
    """Check if required system dependencies are installed"""
    dependencies = ["ffmpeg", "pipx"]
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
            if "ffmpeg" in missing:
                print("sudo apt install -y ffmpeg")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            if "pipx" in missing:
                print("sudo dnf install -y pipx")
            if "ffmpeg" in missing:
                print("sudo dnf install -y ffmpeg")
        else:
            print(f"Please install: {' '.join(missing)}")
        return False
    return True

def print_stage(stage_num, total_stages, stage_name):
    """Print a formatted installation stage"""
    print(f"\n[{stage_num}/{total_stages}] {stage_name}")

def install_with_pipx(skip_whisper=False):
    """Install the application using pipx"""
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

# Add the current directory to the path so we can import from blaze
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from blaze.constants import APP_VERSION

setup(
    name="syllablaze",
    version=APP_VERSION,
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
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
        
        # Create a subprocess with Popen to get real-time output
        process = subprocess.Popen(
            ["pipx", "install", ".", "--force", "--verbose", "--verbose"],  # Double verbose for maximum detail
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Process output line by line
        print("  Verbose installation progress:")
        current_package = None
        pip_install_started = False
        
        for line in iter(process.stdout.readline, ""):
            # Filter and display the most relevant verbose output
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check for package installation indicators
            for package in requirements:
                if package in line and "Installing" in line and package != current_package:
                    current_package = package
                    print(f"\n  [STAGE 3.{requirements.index(package)+1}/{len(requirements)}] Installing {package}...")
                    break
            
            # Show pip install progress
            if "pip install" in line and not pip_install_started:
                pip_install_started = True
                print("  Starting pip installation process...")
            
            # Show download progress
            if "Downloading" in line or "Processing" in line:
                print(f"    {line}")
            
            # Show build/wheel progress
            if "Building wheel" in line or "Created wheel" in line:
                print(f"    {line}")
                
            # Show successful installation messages
            if "Successfully installed" in line:
                packages_installed = line.replace("Successfully installed", "").strip()
                print(f"    Successfully installed: {packages_installed}")
                print("    Please wait... ", end="", flush=True)
                
                # Start a simple spinner animation
                import threading
                import time
                import itertools
                
                # Define the spinner animation
                def spin():
                    spinner = itertools.cycle(['-', '/', '|', '\\'])
                    while not process.poll():
                        sys.stdout.write(next(spinner))
                        sys.stdout.flush()
                        time.sleep(0.1)
                        sys.stdout.write('\b')
                        sys.stdout.flush()
                
                # Start the spinner in a separate thread
                spinner_thread = threading.Thread(target=spin)
                spinner_thread.daemon = True
                spinner_thread.start()
                
            # Show package installation completion
            if "installed package" in line and "syllablaze" in line:
                print(f"    {line}")
        
        # Wait for process to complete
        print("\n  Waiting for installation to complete...")
        process.wait()
        
        # Make sure we close stdout to prevent resource leaks
        process.stdout.close()
        
        # Check if installation was successful
        if process.returncode == 0:
            print("\n  [SUCCESS] Installation process completed successfully.")
        else:
            print(f"\n  [ERROR] Installation failed with return code {process.returncode}")
            print("  Error details:")
            # We don't need to try/except here since we're not using timeout anymore
            # and stdout should still be open
            error_output = process.stdout.readlines()
            if error_output:
                for line in error_output[-10:]:  # Show last 10 lines
                    print(f"    {line.strip()}")
            return False
        
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
    except:
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
        
        # Copy desktop file
        desktop_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "org.kde.syllablaze.desktop")
        desktop_dst = os.path.join(app_dir, "org.kde.syllablaze.desktop")
        shutil.copy2(desktop_src, desktop_dst)
        
        # Set proper permissions for desktop file
        os.chmod(desktop_dst, 0o644)  # rw-r--r--
        
        # Copy icon from resources directory
        icon_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "syllablaze.png")
        icon_dst = os.path.join(icon_dir, "syllablaze.png")
        shutil.copy2(icon_src, icon_dst)
        
        # Also copy icon to applications directory for better compatibility
        icon_app_dst = os.path.join(app_dir, "syllablaze.png")
        shutil.copy2(icon_src, icon_app_dst)
        
        # Make run script executable
        run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run-syllablaze.sh")
        os.chmod(run_script, 0o755)  # rwxr-xr-x
        
        # Update desktop database
        try:
            subprocess.run(["update-desktop-database", app_dir], check=False)
        except:
            pass  # Not critical if this fails
            
        # Force KDE to refresh its menu cache
        try:
            subprocess.run(["kbuildsycoca5"], check=False)
        except:
            try:
                subprocess.run(["kbuildsycoca6"], check=False)  # For newer KDE versions
            except:
                pass  # Not critical if this fails
            
        print("  [SUCCESS] Desktop integration files installed successfully")
        print(f"    Desktop file: {desktop_dst}")
        print(f"    Icon: {icon_dst}")
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
    return parser.parse_args()

def check_if_already_installed():
    """Check if Syllablaze is already installed with pipx"""
    try:
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "syllablaze" in result.stdout:
            print("[INFO] Syllablaze is already installed with pipx.")
            print("[INFO] If you want to reinstall, first run: pipx uninstall syllablaze")
            for line in result.stdout.splitlines():
                if "syllablaze" in line:
                    print(f"  {line.strip()}")
            return True
        return False
    except subprocess.CalledProcessError:
        return False

def run_installation(skip_whisper=False):
    """Run the complete installation process with stages"""
    # Check if already installed
    if check_if_already_installed():
        return False
        
    # Check system dependencies
    if not check_system_dependencies():
        print("Missing system dependencies. Please install them and try again.")
        return False
    
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
    return True

if __name__ == "__main__":
    # Suppress ALSA errors
    suppress_alsa_errors()
    
    # Parse arguments
    args = parse_arguments()
    
    # Run installation
    try:
        if not run_installation(skip_whisper=args.skip_whisper):
            sys.exit(1)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInstallation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Installation failed with error: {e}")
        sys.exit(1)
