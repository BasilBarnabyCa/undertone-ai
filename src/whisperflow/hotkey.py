"""Global hold-to-talk hotkey listener (pynput; needs Input Monitoring permission)."""

import logging
from collections.abc import Callable

from pynput import keyboard

log = logging.getLogger(__name__)

KEYMAP = {
    "right_option": keyboard.Key.alt_r,
    "left_option": keyboard.Key.alt_l,
    "right_command": keyboard.Key.cmd_r,
    "right_ctrl": keyboard.Key.ctrl_r,
    "f13": keyboard.Key.f13,
}


class HoldHotkey:
    """Calls on_start when the key goes down, on_stop when it comes back up."""

    def __init__(
        self, key_name: str, on_start: Callable[[], None], on_stop: Callable[[], None]
    ) -> None:
        if key_name not in KEYMAP:
            log.warning("unknown hotkey %r, falling back to right_option", key_name)
        self.key = KEYMAP.get(key_name, keyboard.Key.alt_r)
        self.on_start = on_start
        self.on_stop = on_stop
        self._held = False
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def _on_press(self, key) -> None:
        if key == self.key and not self._held:
            self._held = True
            self.on_start()

    def _on_release(self, key) -> None:
        if key == self.key and self._held:
            self._held = False
            self.on_stop()
