#!/usr/bin/env python3

import os
import shutil
from pathlib import Path
import sys
import subprocess
import pkg_resources
import warnings

def check_pip():
    try:
        import pip
        return True
    except ImportError:
        return False

def check_system_dependencies():
    """Check if required system dependencies are installed"""
    dependencies = ["ffmpeg"]
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
            print(f"sudo apt install -y {' '.join(missing)}")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            print(f"sudo dnf install -y {' '.join(missing)}")
        else:
            print(f"Please install: {' '.join(missing)}")
        return False
    return True

def install_requirements():
    """Install required Python packages"""
    if not check_pip():
        print("pip is not installed. Please install pip first.")
        return False
        
    print("Installing required packages...")
    try:
        # Install latest whisper from GitHub first
        print("Installing latest Whisper from GitHub...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '--user',
            'git+https://github.com/openai/whisper.git'
        ])
        
        # Install other requirements
        print("Installing other dependencies...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', '-r', 'requirements.txt'])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
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

def install_application():
    # Define paths
    home = Path.home()
    app_name = "syllablaze"
    
    # Check system dependencies
    if not check_system_dependencies():
        print("Missing system dependencies. Please install them and try again.")
        return False
    
    # Check and install requirements first
    if not install_requirements():
        print("Failed to install required packages. Installation aborted.")
        return False
    
    # Create application directories
    app_dir = home / ".local/share/syllablaze"
    bin_dir = home / ".local/bin"
    desktop_dir = home / ".local/share/applications"
    icon_dir = home / ".local/share/icons/hicolor/256x256/apps"
    
    # Create directories if they don't exist
    for directory in [app_dir, bin_dir, desktop_dir, icon_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Copy application files
    python_files = ["main.py", "recorder.py", "transcriber.py", "settings.py", 
                   "progress_window.py", "processing_window.py", "settings_window.py",
                   "loading_window.py", "shortcuts.py", "volume_meter.py"]
    
    for file in python_files:
        if os.path.exists(file):
            shutil.copy2(file, app_dir)
        else:
            print(f"Warning: Could not find {file}")
    
    # Copy requirements.txt
    if os.path.exists('requirements.txt'):
        shutil.copy2('requirements.txt', app_dir)
    
    # Create launcher script with proper Python path
    launcher_path = bin_dir / app_name
    with open(launcher_path, 'w') as f:
        f.write(f'''#!/bin/bash
export PYTHONPATH="$HOME/.local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages:$PYTHONPATH"
cd {app_dir}
exec python3 {app_dir}/main.py "$@"
''')
    
    # Make launcher executable
    launcher_path.chmod(0o755)
    
    # Copy desktop file
    desktop_file = "org.kde.telly_spelly.desktop"  # Will be renamed in a future update
    if os.path.exists(desktop_file):
        # Update the desktop file content
        with open(desktop_file, 'r') as f:
            content = f.read()
        
        # Replace telly-spelly with syllablaze
        content = content.replace("Telly Spelly", "Syllablaze")
        content = content.replace("telly-spelly", "syllablaze")
        
        # Write the updated desktop file
        new_desktop_file = "org.kde.syllablaze.desktop"
        with open(new_desktop_file, 'w') as f:
            f.write(content)
        
        # Copy the new desktop file
        shutil.copy2(new_desktop_file, desktop_dir)
    else:
        print(f"Warning: Could not find {desktop_file}")
    
    # Copy icon
    icon_file = "telly-spelly.png"  # Will be renamed in a future update
    if os.path.exists(icon_file):
        # Copy with the new name
        shutil.copy2(icon_file, icon_dir / "syllablaze.png")
    else:
        print(f"Warning: Could not find {icon_file}")
    
    print("Installation completed!")
    print(f"Application installed to: {app_dir}")
    print("You may need to log out and back in for the application to appear in your menu")
    return True

def verify_installation():
    """Verify that the application was installed correctly"""
    home = Path.home()
    
    # Check application files
    app_dir = home / ".local/share/syllablaze"
    if not app_dir.exists():
        print("Warning: Application directory not found")
        return False
        
    # Check launcher
    launcher = home / ".local/bin/syllablaze"
    if not launcher.exists():
        print("Warning: Launcher script not found")
        return False
        
    # Check desktop file
    desktop_file = home / ".local/share/applications/org.kde.syllablaze.desktop"
    if not desktop_file.exists():
        print("Warning: Desktop file not found")
        return False
        
    # Check icon
    icon_file = home / ".local/share/icons/hicolor/256x256/apps/syllablaze.png"
    if not icon_file.exists():
        print("Warning: Icon file not found")
        return False
        
    print("Installation verified successfully!")
    return True

if __name__ == "__main__":
    try:
        # Suppress ALSA errors
        suppress_alsa_errors()
        
        # Install the application
        success = install_application()
        
        # Verify the installation
        if success:
            verify_installation()
            
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Installation failed: {e}")
        sys.exit(1)
