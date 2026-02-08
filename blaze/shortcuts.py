from PyQt6.QtCore import QObject, pyqtSignal, QMetaObject, Qt, Q_ARG, pyqtSlot
import logging
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

logger = logging.getLogger(__name__)


class GlobalShortcuts(QObject):
    toggle_recording_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.listener = None
        self.current_keys = set()
        self.hotkey_combination = None
        self._last_trigger_time = 0
        self._debounce_ms = 300  # Prevent multiple triggers within 300ms

    def setup_shortcuts(self, toggle_key="Alt+Space"):
        """Setup global keyboard shortcut using pynput

        Args:
            toggle_key: Key combination string (e.g., "Ctrl+Alt+R", "Alt+Space", "Meta+Space")
        """
        try:
            # Remove any existing shortcuts
            self.remove_shortcuts()

            # Parse the key combination
            self.hotkey_combination = self._parse_key_combination(toggle_key)
            if not self.hotkey_combination:
                logger.error(f"Failed to parse key combination: {toggle_key}")
                return False

            # Start keyboard listener
            self.listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release
            )
            self.listener.start()

            # Give the listener a moment to fully initialize
            import time

            time.sleep(0.05)  # 50ms should be enough

            logger.info(f"Global shortcut registered: {toggle_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to register global shortcut: {e}")
            return False

    def _parse_key_combination(self, key_string):
        """Parse Qt-style key combination string

        Supports format: "Ctrl+Alt+R", "Meta+Space", "Alt+Space"
        """
        # Normalize to lowercase and remove angle brackets if present
        key_string = key_string.lower().strip().replace("<", "").replace(">", "")

        # Convert Qt style to pynput style
        key_string = key_string.replace("ctrl", "ctrl")
        key_string = key_string.replace("alt", "alt")
        key_string = key_string.replace("shift", "shift")
        key_string = key_string.replace("meta", "cmd")  # Meta = Super/Windows/Cmd key
        key_string = key_string.replace("super", "cmd")

        # Split by + to get individual keys
        parts = [p.strip() for p in key_string.split("+")]

        keys = set()
        for part in parts:
            # Map common key names to pynput Key enum
            if part in ["ctrl", "control"]:
                keys.add(Key.ctrl_l)  # Use left ctrl
            elif part in ["alt"]:
                keys.add(Key.alt_l)  # Use left alt
            elif part in ["shift"]:
                keys.add(Key.shift_l)  # Use left shift
            elif part in ["cmd", "win", "windows", "super"]:
                keys.add(Key.cmd)  # Super/Windows/Meta key
            elif part == "space":
                keys.add(Key.space)
            elif part == "enter" or part == "return":
                keys.add(Key.enter)
            elif part == "tab":
                keys.add(Key.tab)
            elif part == "esc" or part == "escape":
                keys.add(Key.esc)
            elif len(part) == 1:
                # Single character key
                keys.add(KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key: {part}")

        return keys if keys else None

    def _on_press(self, key):
        """Called when a key is pressed"""
        try:
            # Normalize the key
            if hasattr(key, "vk") and key.vk:
                # Use the virtual key code for comparison
                normalized_key = key
            else:
                normalized_key = key

            self.current_keys.add(normalized_key)

            # Check if current keys match hotkey combination
            if self.hotkey_combination and self._keys_match():
                # Debounce: prevent multiple triggers in quick succession
                import time

                current_time = time.time() * 1000  # Convert to milliseconds
                if current_time - self._last_trigger_time < self._debounce_ms:
                    return
                self._last_trigger_time = current_time

                logger.info("Global hotkey activated!")
                # Emit signal in the main Qt thread to avoid blocking
                QMetaObject.invokeMethod(
                    self, "_emit_trigger_signal", Qt.ConnectionType.QueuedConnection
                )

        except Exception as e:
            logger.error(f"Error in key press handler: {e}")

    def _on_release(self, key):
        """Called when a key is released"""
        try:
            # Remove from current keys
            if hasattr(key, "vk") and key.vk:
                normalized_key = key
            else:
                normalized_key = key

            self.current_keys.discard(normalized_key)

        except Exception as e:
            logger.error(f"Error in key release handler: {e}")

    def _keys_match(self):
        """Check if currently pressed keys match the hotkey combination"""
        if not self.hotkey_combination:
            return False

        # For each key in the hotkey combination, check if it or its equivalent is pressed
        for required_key in self.hotkey_combination:
            found = False

            for pressed_key in self.current_keys:
                if self._keys_equivalent(required_key, pressed_key):
                    found = True
                    break

            if not found:
                return False

        # Also check we don't have extra keys pressed (exact match)
        if len(self.current_keys) != len(self.hotkey_combination):
            return False

        return True

    def _keys_equivalent(self, key1, key2):
        """Check if two keys are equivalent (handles left/right modifiers)"""
        # Direct match
        if key1 == key2:
            return True

        # Check for left/right modifier equivalence
        equivalents = {
            Key.ctrl_l: Key.ctrl_r,
            Key.ctrl_r: Key.ctrl_l,
            Key.alt_l: Key.alt_r,
            Key.alt_r: Key.alt_l,
            Key.shift_l: Key.shift_r,
            Key.shift_r: Key.shift_l,
        }

        return equivalents.get(key1) == key2

    @pyqtSlot()
    def _emit_trigger_signal(self):
        """Emit the trigger signal (called in Qt main thread)"""
        self.toggle_recording_triggered.emit()

    def remove_shortcuts(self):
        """Remove existing shortcuts"""
        if self.listener:
            try:
                self.listener.stop()
                # Give the listener thread time to fully stop
                import time

                time.sleep(0.1)
                self.listener = None
                logger.info("Global shortcuts removed")
            except Exception as e:
                logger.error(f"Error removing shortcuts: {e}")

        self.current_keys.clear()
        self.hotkey_combination = None

    def __del__(self):
        self.remove_shortcuts()
