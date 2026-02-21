"""
Window Settings Manager for Syllablaze

Centralizes all window-related settings management, including synchronization
between QSettings and KWin rules. This prevents bugs caused by inconsistent
state between settings storage and window manager configuration.

Architecture:
- Single source of truth for window settings
- Atomic updates (QSettings + KWin rules updated together)
- Validation and error reporting
- Wayland/KWin-first approach (KWin rules are primary control)
"""

import logging
import subprocess
from blaze.settings import Settings
from blaze.kwin_rules import (
    create_or_update_kwin_rule,
    find_or_create_rule_group,
    KWINRULESRC,
)

logger = logging.getLogger(__name__)


class WindowSettingsManager:
    """
    Manages window-related settings with automatic synchronization
    between QSettings and KWin rules.
    """

    def __init__(self):
        self.settings = Settings()

    def set_always_on_top(self, window_name, setting_key, value):
        """
        Set the always-on-top state for a window.

        This method atomically updates both QSettings and KWin rules to ensure
        consistency. On Wayland/KWin, the KWin rule is the actual control mechanism.

        Args:
            window_name (str): Name of the window (for logging/debugging)
            setting_key (str): QSettings key to update
            value (bool): Whether window should stay on top

        Returns:
            tuple: (success: bool, error_message: str or None)

        Example:
            success, error = manager.set_always_on_top(
                "Recording Dialog",
                "recording_dialog_always_on_top",
                True
            )
            if not success:
                logger.error(f"Failed to update always-on-top: {error}")
        """
        logger.info(f"WindowSettingsManager: Setting {window_name} always-on-top to {value}")

        try:
            # Step 1: Update QSettings (user preference storage)
            self.settings.set(setting_key, value)
            logger.info(f"QSettings updated: {setting_key}={value}")

            # Step 2: Update KWin rule (actual window manager control on Wayland/KWin)
            success = create_or_update_kwin_rule(enable_keep_above=value)
            if not success:
                error_msg = "KWin rule update failed (kwriteconfig6 error)"
                logger.error(f"WindowSettingsManager: {error_msg}")
                return False, error_msg

            logger.info("KWin rule updated successfully")

            # Step 3: Reconfigure KWin to apply changes immediately
            try:
                subprocess.run(
                    ["qdbus", "org.kde.KWin", "/KWin", "reconfigure"],
                    capture_output=True,
                    timeout=2
                )
                logger.info("KWin reconfigured to apply rule changes")
            except Exception as e:
                logger.warning(f"Failed to reconfigure KWin: {e}")
                # Not critical - rule will apply on next window show

            # Step 4: Verify the KWin rule was actually written
            try:
                group = find_or_create_rule_group()
                result = subprocess.run(
                    ["kreadconfig6", "--file", KWINRULESRC, "--group", group, "--key", "above"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    actual_value = result.stdout.strip()
                    expected_value = "true" if value else "false"

                    if actual_value != expected_value:
                        error_msg = f"KWin rule verification FAILED: expected {expected_value}, got {actual_value}"
                        logger.error(f"WindowSettingsManager: {error_msg}")
                        return False, error_msg
                    else:
                        logger.info(f"KWin rule verified: above={actual_value}")
                else:
                    logger.warning(f"Could not verify KWin rule: {result.stderr}")
                    # Not critical - assume update succeeded
            except Exception as e:
                logger.warning(f"Could not verify KWin rule: {e}")
                # Not critical - assume update succeeded

            logger.info(f"WindowSettingsManager: Successfully updated {window_name} always-on-top to {value}")
            return True, None

        except Exception as e:
            error_msg = f"Unexpected error updating always-on-top: {e}"
            logger.error(f"WindowSettingsManager: {error_msg}", exc_info=True)
            return False, error_msg

    def get_always_on_top(self, setting_key):
        """
        Get the current always-on-top setting.

        Args:
            setting_key (str): QSettings key to read

        Returns:
            bool: Current always-on-top state
        """
        value = self.settings.get(setting_key)
        logger.debug(f"WindowSettingsManager: get_always_on_top({setting_key}) = {value}")
        return value

    def initialize_kwin_rule(self, window_name, setting_key):
        """
        Initialize KWin rule to match current QSettings value.

        This should be called during window initialization to ensure
        the KWin rule matches the user's saved preference.

        Args:
            window_name (str): Name of the window (for logging)
            setting_key (str): QSettings key to read

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        logger.info(f"WindowSettingsManager: Initializing KWin rule for {window_name}")

        try:
            current_value = self.settings.get(setting_key)
            logger.info(f"Current setting: {setting_key}={current_value}")

            success = create_or_update_kwin_rule(enable_keep_above=current_value)
            if not success:
                error_msg = "Failed to initialize KWin rule"
                logger.warning(f"WindowSettingsManager: {error_msg}")
                return False, error_msg

            logger.info(f"KWin rule initialized successfully with always_on_top={current_value}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to initialize KWin rule: {e}"
            logger.error(f"WindowSettingsManager: {error_msg}", exc_info=True)
            return False, error_msg
