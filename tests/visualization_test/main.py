"""
Main entry point for visualization test app.
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from main_window import VisualizationWindow
from config import ConfigManager


def main():
    """Main entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SyllablazeVisualizationTest")

    # Create config manager
    config = ConfigManager()

    # Create main window
    window = VisualizationWindow(config)
    window.show()

    print("=" * 50)
    print("Syllablaze Visualization Test")
    print("=" * 50)
    print()
    print("Controls:")
    print("  Left-click:     Play/Pause simulation")
    print("  Middle-click:   Switch visualization pattern")
    print("  Right-click:    Open config in helix editor")
    print("  Drag:           Move window")
    print()
    print("Configuration file:")
    print(f"  {config.config_path}")
    print()
    print("Edit the config file and save to see changes immediately!")
    print("=" * 50)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
