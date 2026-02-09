from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence
import logging

logger = logging.getLogger(__name__)

# kglobalaccel D-Bus constants
KGLOBALACCEL_BUS_NAME = "org.kde.kglobalaccel"
KGLOBALACCEL_OBJECT_PATH = "/kglobalaccel"
KGLOBALACCEL_IFACE = "org.kde.KGlobalAccel"
COMPONENT_IFACE = "org.kde.kglobalaccel.Component"

# Qt modifier and key constants (fallback for _shortcut_to_qt_int)
_MODIFIER_MAP = {
    "ctrl": 0x04000000,
    "alt": 0x08000000,
    "shift": 0x02000000,
    "meta": 0x10000000,
}

_KEY_MAP = {
    "space": 0x20,
    "enter": 0x01000004,
    "return": 0x01000004,
    "tab": 0x01000001,
    "escape": 0x01000000,
    "backspace": 0x01000003,
    "delete": 0x01000007,
    "home": 0x01000010,
    "end": 0x01000011,
    "pageup": 0x01000016,
    "pagedown": 0x01000017,
    "up": 0x01000013,
    "down": 0x01000015,
    "left": 0x01000012,
    "right": 0x01000014,
}

# F1-F12
for _i in range(1, 13):
    _KEY_MAP[f"f{_i}"] = 0x01000030 + _i - 1


def _action_id():
    """Return the 4-element action ID list used by kglobalaccel."""
    return [
        "org.kde.syllablaze", "ToggleRecording",
        "Syllablaze", "Toggle Recording",
    ]


class GlobalShortcuts(QObject):
    toggle_recording_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._bus = None
        self._kglobalaccel_iface = None
        self._current_display = None

    async def setup_shortcuts(self, bus, toggle_key="Alt+Space"):
        """Register shortcut with KDE kglobalaccel via D-Bus.

        Sets toggle_key as the default shortcut. If the user has already
        customized the shortcut in KDE System Settings, their choice is
        preserved (we only set the default, not the active shortcut).

        Args:
            bus: A connected dbus_next.aio.MessageBus instance.
            toggle_key: Default key combination string (e.g. "Alt+Space").

        Returns:
            True if successful, False otherwise
        """
        self._bus = bus
        action_id = _action_id()

        try:
            introspection = await bus.introspect(
                KGLOBALACCEL_BUS_NAME, KGLOBALACCEL_OBJECT_PATH
            )
            proxy = bus.get_proxy_object(
                KGLOBALACCEL_BUS_NAME, KGLOBALACCEL_OBJECT_PATH, introspection
            )
            iface = proxy.get_interface(KGLOBALACCEL_IFACE)
            self._kglobalaccel_iface = iface

            key_int = self._shortcut_to_qt_int(toggle_key)

            # Register the action and set the DEFAULT shortcut only.
            # Flag 0x02 = set default. We do NOT call with 0x00 (set active)
            # so that user customizations from KDE System Settings are preserved.
            await iface.call_do_register(action_id)
            await iface.call_set_shortcut(action_id, [key_int], 0x02)

            # Query the actual active shortcut (may differ from default
            # if user customized it in KDE System Settings)
            current_keys = await iface.call_shortcut(action_id)
            if current_keys and len(current_keys) > 0 and current_keys[0] != 0:
                seq = QKeySequence(current_keys[0])
                self._current_display = seq.toString() or toggle_key
            else:
                self._current_display = toggle_key

            logger.info(
                "kglobalaccel: registered action, default=%s, active=%s",
                toggle_key, self._current_display
            )

            # Subscribe to the activation signal on the component path
            await self._subscribe_to_signal(bus, iface)

            return True

        except Exception as e:
            logger.error(f"kglobalaccel: failed to register shortcut: {e}")
            self._kglobalaccel_iface = None
            return False

    async def _subscribe_to_signal(self, bus, iface):
        """Subscribe to globalShortcutPressed on our component."""
        try:
            component_path = await iface.call_get_component(
                "org.kde.syllablaze"
            )
            logger.info(f"kglobalaccel: component path: {component_path}")

            comp_introspection = await bus.introspect(
                KGLOBALACCEL_BUS_NAME, component_path
            )
            comp_proxy = bus.get_proxy_object(
                KGLOBALACCEL_BUS_NAME, component_path, comp_introspection
            )
            comp_iface = comp_proxy.get_interface(COMPONENT_IFACE)
            comp_iface.on_global_shortcut_pressed(self._on_shortcut_pressed)
            logger.info("kglobalaccel: subscribed to globalShortcutPressed")

        except Exception as e:
            logger.warning(f"kglobalaccel: signal subscription failed: {e}")

    def _on_shortcut_pressed(self, component, shortcut, timestamp):
        """Called when KDE fires globalShortcutPressed on our component."""
        logger.info(
            f"kglobalaccel: shortcut pressed: {shortcut}"
        )
        if shortcut == "ToggleRecording":
            self.toggle_recording_triggered.emit()

    async def query_current_shortcut(self):
        """Query kglobalaccel for the current active shortcut display string.

        Returns the human-readable shortcut string, or None if unavailable.
        """
        if not self._kglobalaccel_iface:
            return self._current_display

        try:
            action_id = _action_id()
            keys = await self._kglobalaccel_iface.call_shortcut(action_id)
            if keys and len(keys) > 0 and keys[0] != 0:
                seq = QKeySequence(keys[0])
                display = seq.toString()
                if display:
                    self._current_display = display
                    return display
        except Exception as e:
            logger.warning(f"kglobalaccel: failed to query shortcut: {e}")

        return self._current_display

    @property
    def current_shortcut_display(self):
        """Last known human-readable shortcut string."""
        return self._current_display

    @staticmethod
    def _shortcut_to_qt_int(key_string):
        """Convert a shortcut string like 'Alt+Space' to a Qt key integer.

        Uses Qt's QKeySequence for correct mapping, with manual fallback.
        """
        try:
            key_sequence = QKeySequence(key_string)
            if not key_sequence.isEmpty():
                qt_key = key_sequence[0]
                key_int = qt_key.toCombined()
                logger.debug(
                    f"_shortcut_to_qt_int: {key_string} -> "
                    f"{hex(key_int)} via QKeySequence"
                )
                return key_int
        except Exception as e:
            logger.warning(
                f"_shortcut_to_qt_int: QKeySequence failed: {e}"
            )

        # Fallback to manual parsing
        parts = [p.strip().lower() for p in key_string.split("+")]
        result = 0
        for part in parts:
            if part in _MODIFIER_MAP:
                result |= _MODIFIER_MAP[part]
            elif part in _KEY_MAP:
                result |= _KEY_MAP[part]
            elif len(part) == 1 and part.isascii():
                result |= ord(part.upper())
            else:
                logger.warning(
                    f"_shortcut_to_qt_int: unknown key '{part}'"
                )
        return result

    def remove_shortcuts(self):
        """No-op. kglobalaccel persists shortcuts across sessions."""
        pass
