"""
KWin Window Rules Manager for Syllablaze

Manages KWin window rules for the recording dialog including:
- Keep above other windows
- Window position (X11 only - Wayland doesn't expose position to clients)
- Window size

Uses kwriteconfig6 to write rules to ~/.config/kwinrulesrc
"""

import subprocess
import logging
import os

logger = logging.getLogger(__name__)

KWINRULESRC = os.path.expanduser("~/.config/kwinrulesrc")
WINDOW_TITLE = "Syllablaze Recording"


def is_wayland():
    """Check if running on Wayland"""
    return os.environ.get("WAYLAND_DISPLAY") is not None


def is_x11():
    """Check if running on X11"""
    return os.environ.get("DISPLAY") is not None and not is_wayland()


def ensure_kwriteconfig_available():
    """Check if kwriteconfig6 is available"""
    try:
        subprocess.run(
            ["which", "kwriteconfig6"], capture_output=True, check=True, timeout=1
        )
        return True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        logger.warning("kwriteconfig6 not found - KWin rules won't be created")
        return False


def find_or_create_rule_group():
    """Find existing Syllablaze rule or assign new group number"""
    # kreadconfig6 doesn't support --list-groups, so parse file directly
    try:
        groups = []
        max_num = 0

        if os.path.exists(KWINRULESRC):
            with open(KWINRULESRC, "r") as f:
                for line in f:
                    line = line.strip()
                    # Look for group headers like [1], [2], etc.
                    if line.startswith("[") and line.endswith("]"):
                        group_name = line[1:-1]
                        if group_name not in ["General", "$Version"]:
                            groups.append(group_name)
                            # Track numeric groups for finding next available number
                            if group_name.isdigit():
                                max_num = max(max_num, int(group_name))

        # Check if our rule already exists
        for group_name in groups:
            try:
                result = subprocess.run(
                    [
                        "kreadconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group_name,
                        "--key",
                        "Description",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if result.returncode == 0 and "Syllablaze Recording" in result.stdout:
                    logger.info(
                        f"Found existing Syllablaze rule in group: {group_name}"
                    )
                    return group_name
            except Exception:
                pass

        # Assign new group number
        new_group = str(max_num + 1)
        logger.info(f"Creating new rule group: {new_group}")
        return new_group

    except Exception as e:
        logger.warning(f"Error finding rule group: {e}")
        return "1"  # Default to group 1


def create_or_update_kwin_rule(enable_keep_above=True, position=None, size=None, on_all_desktops=None):
    """
    Create or update KWin window rule for Syllablaze recording dialog

    Args:
        enable_keep_above (bool): Whether to enable "keep above" property
        position (tuple): Optional (x, y) position to force
        size (tuple): Optional (width, height) size to force
        on_all_desktops (bool or None): True/False to force all-desktops; None leaves the rule untouched
    """
    if not ensure_kwriteconfig_available():
        return False

    try:
        group = find_or_create_rule_group()

        logger.info(
            f"Creating/updating KWin rule for recording dialog (keep_above={enable_keep_above}, position={position}, size={size})"
        )

        # Write rule properties using kwriteconfig6
        commands = [
            # First, set the General section with count and rules
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                "General",
                "--key",
                "count",
                "1",
            ],
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                "General",
                "--key",
                "rules",
                group,
            ],
            # Then write the rule properties
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "Description",
                "Syllablaze Recording - Keep Above",
            ],
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "title",
                WINDOW_TITLE,
            ],
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "titlematch",
                "1",
            ],  # 1 = Exact match
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "above",
                "true" if enable_keep_above else "false",
            ],
            [
                "kwriteconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "aboverule",
                "3" if enable_keep_above else "0",
            ],  # 3=Force, 0=Don't affect
        ]

        # Add position if provided
        if position is not None:
            x, y = position
            commands.extend(
                [
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "position",
                        f"{x},{y}",
                    ],
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "positionrule",
                        "3",
                    ],  # 3 = Force
                ]
            )

        # Add size if provided
        if size is not None:
            width, height = size
            commands.extend(
                [
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "size",
                        f"{width},{height}",
                    ],
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "sizerule",
                        "3",
                    ],  # 3 = Force
                ]
            )

        # Add on-all-desktops if specified
        if on_all_desktops is not None:
            commands.extend(
                [
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "onalldesktops",
                        "true" if on_all_desktops else "false",
                    ],
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "onalldesktopsrule",
                        "3" if on_all_desktops else "0",
                    ],  # 3=Force, 0=Don't affect
                ]
            )

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


def save_window_position_to_rule(x, y, width=None, height=None):
    """
    Save window position (and optionally size) to the KWin rule.

    IMPORTANT: On Wayland, applications cannot reliably determine their window position.
    The x,y values will typically be 0,0. In this case, we skip saving the position
    but still save the size. The user should use KDE's "Configure Special Window Settings"
    to set the initial position on Wayland.

    On X11, this works correctly and the position will be restored.

    Args:
        x (int): X coordinate (ignored on Wayland if 0,0)
        y (int): Y coordinate (ignored on Wayland if 0,0)
        width (int): Optional width
        height (int): Optional height
    """
    if not ensure_kwriteconfig_available():
        return False

    try:
        group = find_or_create_rule_group()

        # On Wayland, don't save position if it's 0,0 (unknown)
        save_position = True
        if is_wayland() and x == 0 and y == 0:
            logger.debug("Wayland detected with position 0,0 - skipping position save")
            save_position = False

        commands = []

        if save_position:
            logger.info(f"Saving window position to KWin rule: ({x}, {y})")
            commands.extend(
                [
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "position",
                        f"{x},{y}",
                    ],
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "positionrule",
                        "3",
                    ],  # 3 = Force
                ]
            )

        if width is not None and height is not None:
            logger.info(f"Saving window size to KWin rule: ({width}, {height})")
            commands.extend(
                [
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "size",
                        f"{width},{height}",
                    ],
                    [
                        "kwriteconfig6",
                        "--file",
                        KWINRULESRC,
                        "--group",
                        group,
                        "--key",
                        "sizerule",
                        "3",
                    ],  # 3 = Force
                ]
            )

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            if result.returncode != 0:
                logger.warning(f"kwriteconfig6 command failed: {' '.join(cmd)}")

        # Reconfigure KWin to reload rules
        reconfigure_kwin()

        logger.info(f"Window settings saved to KWin rule (group={group})")
        return True

    except Exception as e:
        logger.error(f"Failed to save position to KWin rule: {e}", exc_info=True)
        return False


def get_saved_position_from_rule():
    """
    Get the saved position from the KWin rule.

    Returns:
        tuple: (x, y) position or (None, None) if not set
    """
    try:
        group = find_or_create_rule_group()

        result = subprocess.run(
            [
                "kreadconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "position",
            ],
            capture_output=True,
            text=True,
            timeout=1,
        )

        if result.returncode == 0 and result.stdout.strip():
            pos_str = result.stdout.strip()
            parts = pos_str.split(",")
            if len(parts) == 2:
                x, y = int(parts[0]), int(parts[1])
                logger.info(f"Got saved position from KWin rule: ({x}, {y})")
                return (x, y)

        return (None, None)

    except Exception as e:
        logger.warning(f"Failed to get position from KWin rule: {e}")
        return (None, None)


def reconfigure_kwin():
    """Tell KWin to reload its configuration"""
    try:
        # Method 1: D-Bus reconfigure
        subprocess.run(
            ["qdbus", "org.kde.KWin", "/KWin", "reconfigure"],
            capture_output=True,
            timeout=2,
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
            [
                "kreadconfig6",
                "--file",
                KWINRULESRC,
                "--group",
                group,
                "--key",
                "Description",
            ],
            capture_output=True,
            text=True,
            timeout=1,
        )

        if "Syllablaze Recording" in desc_result.stdout:
            # Delete the entire group
            subprocess.run(
                ["kwriteconfig6", "--file", KWINRULESRC, "--group", group, "--delete"],
                capture_output=True,
                timeout=2,
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
