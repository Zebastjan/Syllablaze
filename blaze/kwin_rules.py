"""
KWin Window Rules Manager for Syllablaze (FALLBACK)

This module is a fallback for systems without PyKF6.KWindowSystem.
Primary method is kde_window_manager.py using native KWindowSystem API.

Manages KWin window rules to set "keep above" for the recording dialog.
Uses kwriteconfig6 to write rules to ~/.config/kwinrulesrc
"""

import subprocess
import logging
import os

logger = logging.getLogger(__name__)

KWINRULESRC = os.path.expanduser("~/.config/kwinrulesrc")
RULE_GROUP = "SyllaRecordingRule"  # Unique identifier
WINDOW_TITLE = "Syllablaze Recording"


def ensure_kwriteconfig_available():
    """Check if kwriteconfig6 is available"""
    try:
        subprocess.run(['which', 'kwriteconfig6'],
                      capture_output=True, check=True, timeout=1)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("kwriteconfig6 not found - KWin rules won't be created")
        return False


def find_or_create_rule_group():
    """Find existing Syllablaze rule or assign new group number"""
    # Read existing kwinrulesrc to find our rule or get next group number
    try:
        result = subprocess.run(
            ['kreadconfig6', '--file', KWINRULESRC, '--list-groups'],
            capture_output=True, text=True, timeout=2
        )

        groups = result.stdout.strip().split('\n') if result.returncode == 0 else []

        # Check if our rule already exists
        for group in groups:
            if group.startswith('[') and group.endswith(']'):
                group_name = group[1:-1]
                # Check if this group is our Syllablaze rule
                desc_result = subprocess.run(
                    ['kreadconfig6', '--file', KWINRULESRC,
                     '--group', group_name, '--key', 'Description'],
                    capture_output=True, text=True, timeout=1
                )
                if 'Syllablaze Recording' in desc_result.stdout:
                    logger.info(f"Found existing Syllablaze rule in group: {group_name}")
                    return group_name

        # Assign new group number (find max numeric group + 1)
        max_num = 0
        for group in groups:
            group_name = group.strip('[]')
            if group_name.isdigit():
                max_num = max(max_num, int(group_name))

        new_group = str(max_num + 1)
        logger.info(f"Creating new rule group: {new_group}")
        return new_group

    except Exception as e:
        logger.warning(f"Error finding rule group: {e}")
        return "1"  # Default to group 1


def create_or_update_kwin_rule(enable_keep_above=True):
    """
    Create or update KWin window rule for Syllablaze recording dialog

    Args:
        enable_keep_above (bool): Whether to enable "keep above" property
    """
    if not ensure_kwriteconfig_available():
        return False

    try:
        group = find_or_create_rule_group()

        logger.info(f"Creating/updating KWin rule for recording dialog (keep_above={enable_keep_above})")

        # Write rule properties using kwriteconfig6
        commands = [
            # First, set the General section with count and rules
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', 'General',
             '--key', 'count', '1'],
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', 'General',
             '--key', 'rules', group],
            # Then write the rule properties
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', group,
             '--key', 'Description', 'Syllablaze Recording - Keep Above'],
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', group,
             '--key', 'title', WINDOW_TITLE],
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', group,
             '--key', 'titlematch', '1'],  # 1 = Exact match
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', group,
             '--key', 'above', 'true' if enable_keep_above else 'false'],
            ['kwriteconfig6', '--file', KWINRULESRC, '--group', group,
             '--key', 'aboverule', '3' if enable_keep_above else '0'],  # 3=Force, 0=Don't affect
        ]

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            if result.returncode != 0:
                logger.warning(f"kwriteconfig6 command failed: {' '.join(cmd)}")
                logger.warning(f"Error: {result.stderr.decode()}")

        # Reconfigure KWin to reload rules
        reconfigure_kwin()

        logger.info(f"KWin rule created/updated successfully (group={group})")
        return True

    except Exception as e:
        logger.error(f"Failed to create KWin rule: {e}", exc_info=True)
        return False


def reconfigure_kwin():
    """Tell KWin to reload its configuration"""
    try:
        # Method 1: D-Bus reconfigure
        subprocess.run(
            ['qdbus', 'org.kde.KWin', '/KWin', 'reconfigure'],
            capture_output=True, timeout=2
        )
        logger.info("Sent reconfigure signal to KWin via D-Bus")
    except Exception as e:
        logger.warning(f"Failed to reconfigure KWin: {e}")


def delete_kwin_rule():
    """Delete the Syllablaze KWin rule"""
    try:
        group = find_or_create_rule_group()

        # Check if it's our rule before deleting
        desc_result = subprocess.run(
            ['kreadconfig6', '--file', KWINRULESRC,
             '--group', group, '--key', 'Description'],
            capture_output=True, text=True, timeout=1
        )

        if 'Syllablaze Recording' in desc_result.stdout:
            # Delete the entire group
            subprocess.run(
                ['kwriteconfig6', '--file', KWINRULESRC,
                 '--group', group, '--delete'],
                capture_output=True, timeout=2
            )
            reconfigure_kwin()
            logger.info(f"Deleted KWin rule from group: {group}")
            return True
        else:
            logger.warning(f"Group {group} is not a Syllablaze rule, skipping deletion")
            return False

    except Exception as e:
        logger.error(f"Failed to delete KWin rule: {e}", exc_info=True)
        return False
