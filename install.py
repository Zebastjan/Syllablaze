#!/usr/bin/env python3

import os
import shutil
from pathlib import Path
import sys
import subprocess
import importlib.metadata
import warnings

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

def install_requirements(debug_mode=True, timeout=300, manual_install=False, skip_whisper=False):
    """Install required Python packages using pipx with enhanced debugging"""
    print("Installing application with pipx...")
    try:
        # Create a temporary directory for the application
        temp_dir = os.path.join(os.getcwd(), "temp_app")
        os.makedirs(temp_dir, exist_ok=True)
        
        print("Preparing application files...")
        # Copy necessary files to the temp directory
        for file in os.listdir():
            if file.endswith(".py") and file not in ["install.py", "uninstall.py"]:
                shutil.copy2(file, temp_dir)
        
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
        
        # Write modified requirements if needed
        if skip_whisper:
            with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
                f.write("\n".join(requirements))
        else:
            shutil.copy2("requirements.txt", temp_dir)
        
        # Create a simple setup.py file for pipx
        print("\nCreating setup configuration...")
        with open(os.path.join(temp_dir, "setup.py"), "w") as f:
            f.write("""
from setuptools import setup

setup(
    name="syllablaze",
    version="0.1.0",
    py_modules=["main"],
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "syllablaze=main:main",
        ],
    },
)
""")
        
        # Install with pipx in verbose mode with real-time output
        print("\nInstalling with pipx (verbose mode)...")
        print("This may take a few minutes. Please be patient.")
        print("If the installation appears to hang, you can press Ctrl+C to cancel and try the alternative installation method.\n")
        
        # First, try to install with pip directly to see if there are any issues
        if debug_mode:
            print("DEBUG: Testing pip installation first...")
            try:
                # Create a virtual environment for testing
                test_venv_dir = os.path.join(os.getcwd(), "test_venv")
                subprocess.run([sys.executable, "-m", "venv", test_venv_dir], check=True)
                
                # Get the pip path
                pip_path = os.path.join(test_venv_dir, "bin", "pip")
                
                # Install the requirements with pip in verbose mode
                print("DEBUG: Installing requirements with pip...")
                pip_process = subprocess.run(
                    [pip_path, "install", "-r", "requirements.txt", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60  # 60 second timeout for the test
                )
                
                print(f"DEBUG: Pip installation test result: {pip_process.returncode}")
                if pip_process.returncode != 0:
                    print("DEBUG: Pip installation test failed. Output:")
                    print(pip_process.stdout)
                    print(pip_process.stderr)
                else:
                    print("DEBUG: Pip installation test succeeded.")
                
                # Clean up test environment
                shutil.rmtree(test_venv_dir, ignore_errors=True)
            except subprocess.TimeoutExpired:
                print("DEBUG: Pip installation test timed out after 60 seconds.")
                shutil.rmtree(test_venv_dir, ignore_errors=True)
            except Exception as e:
                print(f"DEBUG: Pip installation test failed with error: {e}")
                shutil.rmtree(test_venv_dir, ignore_errors=True)
        
        # Check if manual installation is requested
        if manual_install:
            print("\nPerforming manual package installation...")
            
            # Create a virtual environment for the application
            venv_dir = os.path.join(os.getcwd(), "venv")
            print(f"Creating virtual environment in {venv_dir}...")
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            
            # Get the pip path
            pip_path = os.path.join(venv_dir, "bin", "pip")
            python_path = os.path.join(venv_dir, "bin", "python")
            
            # Install each package individually with progress reporting
            for i, package in enumerate(requirements, 1):
                print(f"\nInstalling package [{i}/{len(requirements)}]: {package}")
                try:
                    # Use subprocess.run with a timeout and --log parameter to show progress
                    log_file = "/tmp/pip.log"
                    print(f"Installing with pip -v --log {log_file} install {package}")
                    result = subprocess.run(
                        [pip_path, "-v", "--log", log_file, "install", package, "--upgrade"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=timeout
                    )
                    
                    # Print the output to show progress
                    if result.stdout:
                        print(result.stdout)
                    
                    if result.returncode == 0:
                        print(f"✓ Successfully installed {package}")
                    else:
                        print(f"✗ Failed to install {package}")
                        
                        # Check for specific errors and provide helpful hints
                        if "portaudio.h: No such file or directory" in result.stdout:
                            print("\nERROR: Missing PortAudio development files required for PyAudio")
                            if os.path.exists("/etc/debian_version"):  # Ubuntu/Debian
                                print("\nTo fix this issue, install the required system package:")
                                print("    sudo apt install -y portaudio19-dev")
                            elif os.path.exists("/etc/fedora-release"):  # Fedora
                                print("\nTo fix this issue, install the required system package:")
                                print("    sudo dnf install -y portaudio-devel")
                            else:
                                print("\nTo fix this issue, install the PortAudio development package for your system")
                            print("\nThen run the installation again.")
                        else:
                            print("Error output:")
                            print(result.stdout)
                            if result.stderr:
                                print(result.stderr)
                        return False
                except subprocess.TimeoutExpired:
                    print(f"✗ Installation of {package} timed out after {timeout} seconds")
                    print(f"This package may need to be installed manually later.")
                    continue
            
            # Install the application itself
            print("\nInstalling Syllablaze application...")
            try:
                subprocess.run(
                    [pip_path, "install", "-e", "."],
                    check=True,
                    cwd=os.getcwd()
                )
                print("✓ Successfully installed Syllablaze")
                
                # Create a shell script to run the application
                script_path = os.path.join(os.getcwd(), "run-syllablaze.sh")
                with open(script_path, "w") as f:
                    f.write(f"""#!/bin/bash
source {venv_dir}/bin/activate
python {os.path.join(os.getcwd(), "main.py")}
""")
                os.chmod(script_path, 0o755)
                print(f"✓ Created executable script: {script_path}")
                
                return True
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install Syllablaze: {e}")
                return False
        else:
            # Proceed with standard pipx installation
            print("\nProceeding with pipx installation...")
            
            # Use Popen to capture and display output in real-time with timeout
            import threading
            import time
            
            # Create a flag to track if the process is still running
            process_running = True
            
            # Function to monitor the process and provide periodic updates
            def monitor_process():
                start_time = time.time()
                while process_running and time.time() - start_time < timeout:
                    time.sleep(10)  # Check every 10 seconds
                    if process_running:
                        elapsed = int(time.time() - start_time)
                        print(f"Still installing... (elapsed: {elapsed}s)")
                
                if process_running and time.time() - start_time >= timeout:
                    print(f"\nWARNING: Installation is taking longer than {timeout} seconds.")
                    print("You may want to cancel (Ctrl+C) and try the alternative installation method.")
                    print("Run with --manual-install to install packages one by one with progress reporting.")
                    if "openai-whisper" in " ".join(requirements):
                        print("Or use --skip-whisper to skip installing the large openai-whisper package.")
            
            # Start the monitor thread
            monitor_thread = threading.Thread(target=monitor_process)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Start the pipx installation process
            process = subprocess.Popen(
                ["pipx", "install", temp_dir, "--force", "--verbose"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Display output in real-time
            for line in process.stdout:
                print(line, end='')
                # If we see the line that indicates pip is running, print additional info
                if "running" in line and "pip" in line and "install" in line:
                    print("\nNOTE: The pip installation step may take several minutes.")
                    print("      This is where the actual package dependencies are being installed.")
                    print("      You will see progress once this step completes.")
                    print("      The openai-whisper package is particularly large and may take a long time.\n")
            
            # Wait for process to complete and check return code
            return_code = process.wait()
            
            # Update the process_running flag
            process_running = False
            
            if return_code != 0:
                print(f"pipx installation failed with return code {return_code}")
                print("\nAlternative installation methods:")
                print("1. Try with manual installation: python3 install.py --manual-install")
                print("2. Try skipping whisper: python3 install.py --skip-whisper")
                print("3. Or install manually:")
                print("   a. Create a virtual environment: python -m venv venv")
                print("   b. Activate it: source venv/bin/activate")
                print("   c. Install requirements: pip install -r requirements.txt")
                print("   d. Run the application: python main.py")
                return False
            
        print("\nCleaning up temporary files...")
        # Clean up
        shutil.rmtree(temp_dir)
        
        print("Installation completed successfully!")
        return True
    except KeyboardInterrupt:
        print("\nInstallation was interrupted by user.")
        print("\nAlternative installation method:")
        print("1. Create a virtual environment: python -m venv venv")
        print("2. Activate it: source venv/bin/activate")
        print("3. Install requirements: pip install -r requirements.txt")
        print("4. Run the application: python main.py")
        return False
    except Exception as e:
        print(f"Failed to install requirements: {e}")
        print("\nAlternative installation method:")
        print("1. Create a virtual environment: python -m venv venv")
        print("2. Activate it: source venv/bin/activate")
        print("3. Install requirements: pip install -r requirements.txt")
        print("4. Run the application: python main.py")
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
        print("Failed to install application with pipx. Installation aborted.")
        return False
    
    # Create application directories
    desktop_dir = home / ".local/share/applications"
    icon_dir = home / ".local/share/icons/hicolor/256x256/apps"
    
    # Create directories if they don't exist
    for directory in [desktop_dir, icon_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        
    # Copy desktop file
    desktop_file = "org.kde.telly_spelly.desktop"  # Will be renamed in a future update
    if os.path.exists(desktop_file):
        # Update the desktop file content
        with open(desktop_file, 'r') as f:
            content = f.read()
        
        # Replace telly-spelly with syllablaze
        content = content.replace("Telly Spelly", "Syllablaze")
        content = content.replace("telly-spelly", "syllablaze")
        
        # Update the Exec line to use pipx
        content = content.replace("Exec=syllablaze", "Exec=pipx run syllablaze")
        
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
    print("You may need to log out and back in for the application to appear in your menu")
    return True

def verify_installation():
    """Verify that the application was installed correctly"""
    home = Path.home()
    
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
        else:
            print("✗ Warning: Syllablaze not found in pipx installed applications")
            return False
    except subprocess.CalledProcessError:
        print("✗ Warning: Failed to verify pipx installation")
        return False
        
    # Check desktop file
    desktop_file = home / ".local/share/applications/org.kde.syllablaze.desktop"
    if desktop_file.exists():
        print(f"✓ Desktop file installed: {desktop_file}")
    else:
        print(f"✗ Warning: Desktop file not found: {desktop_file}")
        return False
        
    # Check icon
    icon_file = home / ".local/share/icons/hicolor/256x256/apps/syllablaze.png"
    if icon_file.exists():
        print(f"✓ Icon file installed: {icon_file}")
    else:
        print(f"✗ Warning: Icon file not found: {icon_file}")
        return False
    
    # Display installed packages
    try:
        print("\nInstalled dependencies:")
        # Get the venv path from pipx list output
        venv_path = None
        for line in result.stdout.splitlines():
            if "syllablaze" in line and "venv" in line:
                parts = line.split("venv:")
                if len(parts) > 1:
                    venv_path = parts[1].strip()
                    break
        
        if venv_path:
            # List installed packages in the venv
            pip_path = os.path.join(venv_path, "bin", "pip")
            if os.path.exists(pip_path):
                pip_list = subprocess.run([pip_path, "list"], capture_output=True, text=True)
                print(pip_list.stdout)
    except Exception as e:
        print(f"Note: Could not list installed packages: {e}")
        
    print("\nInstallation verified successfully!")
    print("You can now run Syllablaze from your applications menu or by typing 'pipx run syllablaze' in terminal")
    return True

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    parser = argparse.ArgumentParser(description="Install Syllablaze application")
    parser.add_argument("--debug", action="store_true", help="Run installation in debug mode")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds for the installation process (default: 300)")
    parser.add_argument("--skip-pipx", action="store_true", help="Skip pipx installation and show alternative method")
    parser.add_argument("--no-manual-install", action="store_true", help="Use pipx instead of manual package installation")
    parser.add_argument("--skip-whisper", action="store_true", help="Skip installing openai-whisper (will need to be installed manually later)")
    args = parser.parse_args()
    
    # Set manual_install to True by default (opposite of no-manual-install)
    args.manual_install = not args.no_manual_install
    return args

if __name__ == "__main__":
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        if args.skip_pipx:
            print("Skipping pipx installation as requested.")
            print("\nAlternative installation method:")
            print("1. Create a virtual environment: python -m venv venv")
            print("2. Activate it: source venv/bin/activate")
            print("3. Install requirements: pip install -r requirements.txt")
            print("4. Run the application: python main.py")
            sys.exit(0)
        
        # Suppress ALSA errors
        suppress_alsa_errors()
        
        # Install the application with debug mode if requested
        print(f"Running installation with {'debug mode enabled' if args.debug else 'debug mode disabled'}")
        print(f"Installation timeout set to {args.timeout} seconds")
        
        # Modify install_application to pass debug_mode and timeout
        def install_application_with_args():
            # Define paths
            home = Path.home()
            app_name = "syllablaze"
            
            # Check system dependencies
            if not check_system_dependencies():
                print("Missing system dependencies. Please install them and try again.")
                return False
            
            # Check and install requirements with all options
            if not install_requirements(
                debug_mode=args.debug,
                timeout=args.timeout,
                manual_install=args.manual_install,
                skip_whisper=args.skip_whisper
            ):
                print("Failed to install application. Installation aborted.")
                return False
            
            # Create application directories
            desktop_dir = home / ".local/share/applications"
            icon_dir = home / ".local/share/icons/hicolor/256x256/apps"
            
            # Create directories if they don't exist
            for directory in [desktop_dir, icon_dir]:
                directory.mkdir(parents=True, exist_ok=True)
                
            # Copy desktop file
            desktop_file = "org.kde.telly_spelly.desktop"  # Will be renamed in a future update
            if os.path.exists(desktop_file):
                # Update the desktop file content
                with open(desktop_file, 'r') as f:
                    content = f.read()
                
                # Replace telly-spelly with syllablaze
                content = content.replace("Telly Spelly", "Syllablaze")
                content = content.replace("telly-spelly", "syllablaze")
                
                # Update the Exec line to use pipx
                content = content.replace("Exec=syllablaze", "Exec=pipx run syllablaze")
                
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
            print("You may need to log out and back in for the application to appear in your menu")
            return True
        
        success = install_application_with_args()
        
        # Verify the installation
        if success:
            verify_installation()
            
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Installation failed: {e}")
        sys.exit(1)
