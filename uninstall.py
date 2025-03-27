#!/usr/bin/env python3

import shutil
import subprocess
import os
from pathlib import Path
import sys

def uninstall_application():
    home = Path.home()
    current_dir = Path.cwd()
    
    print("Uninstalling Syllablaze...")
    
    # Remove pipx installation if it exists
    print("Checking for pipx installation and related files...")
    
    # Directly check for pipx venv directory
    pipx_venv_dir = home / ".local/share/pipx/venvs/syllablaze"
    if pipx_venv_dir.exists():
        print(f"Removing pipx venv directory: {pipx_venv_dir}")
        try:
            shutil.rmtree(pipx_venv_dir)
        except Exception as e:
            print(f"Error removing pipx venv directory: {e}")
    else:
        print(f"Pipx venv directory not found: {pipx_venv_dir}")
        
    # Check for pipx bin symlinks
    pipx_bin_dir = home / ".local/share/pipx/bin"
    if pipx_bin_dir.exists():
        print(f"Checking pipx bin directory: {pipx_bin_dir}")
        for item in pipx_bin_dir.iterdir():
            if "syllablaze" in item.name:
                print(f"Removing pipx bin symlink: {item}")
                try:
                    item.unlink()
                except Exception as e:
                    print(f"Error removing pipx bin symlink: {e}")
    else:
        print(f"Pipx bin directory not found: {pipx_bin_dir}")
    
    # Check for pipx cache files
    pipx_cache_dir = home / ".cache/pipx"
    if pipx_cache_dir.exists():
        print(f"Checking pipx cache directory: {pipx_cache_dir}")
        # Find all syllablaze-related files in the pipx cache
        for root, dirs, files in os.walk(pipx_cache_dir):
            for item in files + dirs:
                if "syllablaze" in item.lower():
                    item_path = Path(root) / item
                    print(f"Removing pipx cache item: {item_path}")
                    try:
                        if item_path.is_dir():
                            shutil.rmtree(item_path)
                        else:
                            item_path.unlink()
                    except Exception as e:
                        print(f"Error removing pipx cache item: {e}")
    
    # Try using pipx command if available
    try:
        print("Trying pipx command...")
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "syllablaze" in result.stdout:
            print("Removing syllablaze with pipx uninstall...")
            subprocess.run(["pipx", "uninstall", "syllablaze"], check=False)
    except Exception as e:
        print(f"Warning: Could not use pipx command: {e}")
    
    # Remove application files
    app_dir = home / ".local/share/syllablaze"
    if app_dir.exists():
        print(f"Removing application directory: {app_dir}")
        shutil.rmtree(app_dir)
    
    # Remove launcher
    launcher = home / ".local/bin/syllablaze"
    if launcher.exists():
        print(f"Removing launcher: {launcher}")
        launcher.unlink()
    
    # Remove run script and its symbolic link
    print("Checking for run scripts and symlinks...")
    
    run_script = current_dir / "run-syllablaze.sh"
    if run_script.exists():
        print(f"Removing run script: {run_script}")
        try:
            run_script.unlink()
        except Exception as e:
            print(f"Error removing run script: {e}")
    else:
        print(f"Run script not found: {run_script}")
    
    # Check for run script link in .local/bin
    run_script_link = home / ".local/bin/run-syllablaze.sh"
    if run_script_link.exists():
        print(f"Removing run script link: {run_script_link}")
        try:
            # Try to use unlink first
            run_script_link.unlink()
        except Exception as e:
            print(f"Error removing run script link with unlink: {e}")
            try:
                # If unlink fails, try using os.remove
                os.remove(run_script_link)
                print(f"Successfully removed run script link with os.remove")
            except Exception as e2:
                print(f"Error removing run script link with os.remove: {e2}")
                try:
                    # If os.remove fails, try using rm command
                    subprocess.run(["rm", "-f", str(run_script_link)], check=True)
                    print(f"Successfully removed run script link with rm command")
                except Exception as e3:
                    print(f"Error removing run script link with rm command: {e3}")
                    print(f"WARNING: Could not remove {run_script_link}. You may need to remove it manually.")
    else:
        print(f"Run script link not found: {run_script_link}")
    
    # Also check for syllablaze launcher in .local/bin
    syllablaze_link = home / ".local/bin/syllablaze"
    if syllablaze_link.exists():
        print(f"Removing syllablaze launcher: {syllablaze_link}")
        try:
            # Try to use unlink first
            syllablaze_link.unlink()
        except Exception as e:
            print(f"Error removing syllablaze launcher with unlink: {e}")
            try:
                # If unlink fails, try using os.remove
                os.remove(syllablaze_link)
                print(f"Successfully removed syllablaze launcher with os.remove")
            except Exception as e2:
                print(f"Error removing syllablaze launcher with os.remove: {e2}")
                try:
                    # If os.remove fails, try using rm command
                    subprocess.run(["rm", "-f", str(syllablaze_link)], check=True)
                    print(f"Successfully removed syllablaze launcher with rm command")
                except Exception as e3:
                    print(f"Error removing syllablaze launcher with rm command: {e3}")
                    print(f"WARNING: Could not remove {syllablaze_link}. You may need to remove it manually.")
    else:
        print(f"Syllablaze launcher not found: {syllablaze_link}")
    
    # Remove desktop file
    desktop_file = home / ".local/share/applications/org.kde.syllablaze.desktop"
    if desktop_file.exists():
        print(f"Removing desktop file: {desktop_file}")
        desktop_file.unlink()
    
    # Remove icon
    icon_file = home / ".local/share/icons/hicolor/256x256/apps/syllablaze.png"
    if icon_file.exists():
        print(f"Removing icon file: {icon_file}")
        icon_file.unlink()
    
    # Remove virtual environment if it exists
    venv_dir = current_dir / "venv"
    if venv_dir.exists():
        print(f"Removing virtual environment: {venv_dir}")
        shutil.rmtree(venv_dir)
    
    # Check for old files (from previous telly-spelly installation)
    old_app_dir = home / ".local/share/telly-spelly"
    if old_app_dir.exists():
        print(f"Removing old application directory: {old_app_dir}")
        shutil.rmtree(old_app_dir)
    
    old_launcher = home / ".local/bin/telly-spelly"
    if old_launcher.exists():
        print(f"Removing old launcher: {old_launcher}")
        old_launcher.unlink()
    
    old_desktop_file = home / ".local/share/applications/org.kde.telly_spelly.desktop"
    if old_desktop_file.exists():
        print(f"Removing old desktop file: {old_desktop_file}")
        old_desktop_file.unlink()
    
    old_icon_file = home / ".local/share/icons/hicolor/256x256/apps/telly-spelly.png"
    if old_icon_file.exists():
        print(f"Removing old icon file: {old_icon_file}")
        old_icon_file.unlink()
    
    # Remove build and egg-info directories if they exist
    build_dir = current_dir / "build"
    if build_dir.exists():
        print(f"Removing build directory: {build_dir}")
        shutil.rmtree(build_dir)
    
    egg_info_dir = current_dir / "syllablaze.egg-info"
    if egg_info_dir.exists():
        print(f"Removing egg-info directory: {egg_info_dir}")
        shutil.rmtree(egg_info_dir)
    
    # Remove temp_app directory if it exists
    temp_app_dir = current_dir / "temp_app"
    if temp_app_dir.exists():
        print(f"Removing temp_app directory: {temp_app_dir}")
        shutil.rmtree(temp_app_dir)
    
    # Remove desktop file in the project directory
    project_desktop_file = current_dir / "org.kde.syllablaze.desktop"
    if project_desktop_file.exists():
        print(f"Removing desktop file in project directory: {project_desktop_file}")
        try:
            project_desktop_file.unlink()
        except Exception as e:
            print(f"Error removing desktop file in project directory: {e}")
            try:
                # If unlink fails, try using os.remove
                os.remove(project_desktop_file)
                print(f"Successfully removed desktop file with os.remove")
            except Exception as e2:
                print(f"Error removing desktop file with os.remove: {e2}")
                try:
                    # If os.remove fails, try using rm command
                    subprocess.run(["rm", "-f", str(project_desktop_file)], check=True)
                    print(f"Successfully removed desktop file with rm command")
                except Exception as e3:
                    print(f"Error removing desktop file with rm command: {e3}")
    
    # Note about KDE favorites menu
    print("\nNOTE: If the application still appears in your KDE favorites menu,")
    print("you may need to log out and log back in, or manually remove it from the menu.")
    
    # Note about whisper models
    whisper_models_dir = home / ".cache/whisper"
    if whisper_models_dir.exists():
        print(f"\nNOTE: Whisper models in {whisper_models_dir} have been preserved.")
        print("These are the .pt files that contain the trained models.")
        print("If you want to remove them as well, you can delete them manually.")
    
    print("\nApplication uninstalled successfully!")

if __name__ == "__main__":
    try:
        uninstall_application()
    except Exception as e:
        print(f"Uninstallation failed: {e}")
        sys.exit(1)
