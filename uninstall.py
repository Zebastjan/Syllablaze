#!/usr/bin/env python3

import shutil
from pathlib import Path
import sys

def uninstall_application():
    home = Path.home()
    
    # Remove application files
    app_dir = home / ".local/share/syllablaze"
    if app_dir.exists():
        shutil.rmtree(app_dir)
    
    # Remove launcher
    launcher = home / ".local/bin/syllablaze"
    if launcher.exists():
        launcher.unlink()
    
    # Remove desktop file
    desktop_file = home / ".local/share/applications/org.kde.syllablaze.desktop"
    if desktop_file.exists():
        desktop_file.unlink()
    
    # Remove icon
    icon_file = home / ".local/share/icons/hicolor/256x256/apps/syllablaze.png"
    if icon_file.exists():
        icon_file.unlink()
    
    # Check for old files (from previous telly-spelly installation)
    old_app_dir = home / ".local/share/telly-spelly"
    if old_app_dir.exists():
        shutil.rmtree(old_app_dir)
    
    old_launcher = home / ".local/bin/telly-spelly"
    if old_launcher.exists():
        old_launcher.unlink()
    
    old_desktop_file = home / ".local/share/applications/org.kde.telly_spelly.desktop"
    if old_desktop_file.exists():
        old_desktop_file.unlink()
    
    old_icon_file = home / ".local/share/icons/hicolor/256x256/apps/telly-spelly.png"
    if old_icon_file.exists():
        old_icon_file.unlink()
    
    print("Application uninstalled successfully!")

if __name__ == "__main__":
    try:
        uninstall_application()
    except Exception as e:
        print(f"Uninstallation failed: {e}")
        sys.exit(1)
