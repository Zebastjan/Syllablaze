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

def install_with_pipx(skip_whisper=False):
    """Install the application using pipx"""
    print("Installing application with pipx...")
    try:
        # Process requirements.txt
        with open("requirements.txt", "r") as f:
            requirements = f.read().splitlines()
            
        # Filter out empty lines and comments
        requirements = [req for req in requirements if req and not req.startswith('#')]
        
        # Remove openai-whisper if skip_whisper is True
        if skip_whisper:
            requirements = [req for req in requirements if "openai-whisper" not in req]
            print("\nNOTE: Skipping openai-whisper as requested. You will need to install it manually later.")
        
        # Display requirements that will be installed
        print("\nPackages that will be installed:")
        for req in requirements:
            print(f"  - {req}")
        
        # Create setup.py file for pipx installation
        print("\nCreating setup configuration...")
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
        print("\nInstalling with pipx...")
        print("This may take a few minutes. Please be patient.")
        
        # Run pipx install command
        process = subprocess.run(
            ["pipx", "install", ".", "--force"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Check if installation was successful
        if process.returncode != 0:
            print(f"pipx installation failed with return code {process.returncode}")
            print(f"Error output: {process.stdout}")
            return False
        
        print("\nInstallation completed successfully!")
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

def verify_installation():
    """Verify that the application was installed correctly"""
    print("\nVerifying installation...")
    
    # Check pipx installation
    try:
        print("Checking pipx installation...")
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "syllablaze" in result.stdout:
            print("✓ Syllablaze successfully installed with pipx")
            # Extract and display the installation path
            for line in result.stdout.splitlines():
                if "syllablaze" in line:
                    print(f"  {line.strip()}")
            return True
        else:
            print("✗ Warning: Syllablaze not found in pipx installed applications")
            return False
    except subprocess.CalledProcessError:
        print("✗ Warning: Failed to verify pipx installation")
        return False

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    parser = argparse.ArgumentParser(description="Install Syllablaze")
    parser.add_argument("--skip-whisper", action="store_true", help="Skip installing the openai-whisper package")
    return parser.parse_args()

if __name__ == "__main__":
    # Suppress ALSA errors
    suppress_alsa_errors()
    
    # Parse arguments
    args = parse_arguments()
    
    # Run installation
    try:
        # Check system dependencies
        if not check_system_dependencies():
            print("Missing system dependencies. Please install them and try again.")
            sys.exit(1)
        
        # Install with pipx
        if not install_with_pipx(skip_whisper=args.skip_whisper):
            print("Failed to install application with pipx. Installation aborted.")
            sys.exit(1)
        
        # Verify installation
        verify_installation()
        
        print("\nYou can now run the application by typing 'syllablaze' in the terminal")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInstallation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Installation failed with error: {e}")
        sys.exit(1)
