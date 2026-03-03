"""
Configuration manager with auto-reload support.
"""

import tomllib
import os
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher


class ConfigManager(QObject):
    """Manages TOML configuration with auto-reload."""

    config_changed = pyqtSignal()  # Emitted when config is reloaded

    def __init__(self, config_path: str = None):
        super().__init__()

        if config_path is None:
            # Default to same directory as this file
            self.config_path = Path(__file__).parent / "viz_config.toml"
        else:
            self.config_path = Path(config_path)

        self._data = {}
        self._current_pattern = "dots_radial"

        # Set up file watcher for auto-reload
        self._watcher = QFileSystemWatcher()
        self._watcher.addPath(str(self.config_path))
        self._watcher.fileChanged.connect(self._on_file_changed)

        # Initial load
        self.load()

    def load(self) -> dict:
        """Load configuration from TOML file."""
        try:
            with open(self.config_path, "rb") as f:
                self._data = tomllib.load(f)

            # Update current pattern
            if "current_pattern" in self._data:
                self._current_pattern = self._data["current_pattern"]

            return self._data
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_defaults()

    def _on_file_changed(self):
        """Handle file change event."""
        print("Config file changed, reloading...")
        self.load()
        self.config_changed.emit()

        # Re-add file to watcher (some editors delete/recreate files)
        if str(self.config_path) not in self._watcher.files():
            self._watcher.addPath(str(self.config_path))

    def get_pattern_params(self, pattern_name: str = None) -> dict:
        """Get parameters for a specific pattern."""
        if pattern_name is None:
            pattern_name = self._current_pattern

        return self._data.get(pattern_name, {})

    @property
    def current_pattern(self) -> str:
        """Get current pattern name."""
        return self._current_pattern

    @current_pattern.setter
    def current_pattern(self, value: str):
        """Set current pattern name (in-memory only, doesn't save to file)."""
        self._current_pattern = value

    def _get_defaults(self) -> dict:
        """Get default configuration."""
        return {
            "current_pattern": "dots_radial",
            "dots_radial": {
                "dot_spacing": 8,
                "dot_radius": 2.5,
                "wave_falloff": 1.5,
                "speed_min": 0.5,
                "speed_max": 4.0,
                "bounce": True,
            },
            "dots_curtains": {
                "dots_per_col": 10,
                "columns_per_side": 2,
                "dot_radius": 3.0,
                "expansion_curve": 0.7,
                "drift_speed": 0.3,
            },
            "dots_radar": {
                "num_dots": 40,
                "dot_radius": 2.5,
                "trail_length": 1.047,
                "speed_min": 0.2,
                "speed_max": 6.0,
                "num_rings": 1,
            },
        }

    def open_in_editor(self):
        """Open configuration file in helix editor."""
        import subprocess

        try:
            subprocess.Popen(["helix", str(self.config_path)])
        except Exception as e:
            print(f"Error opening editor: {e}")
