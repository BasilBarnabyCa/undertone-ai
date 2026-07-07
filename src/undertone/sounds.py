"""Optional start/stop audio cues via macOS system sounds (NSSound).

Off by default. Both sounds are loaded up front (cheap) so the menu toggle can
enable/disable playback live without rebuilding anything; `enabled` gates
whether play() actually makes noise. Playback is marshalled to the main thread
because the hotkey callbacks arrive on the pynput listener thread.
"""

import logging

from AppKit import NSSound
from PyObjCTools import AppHelper

log = logging.getLogger(__name__)


def _load(name: str, volume: float) -> NSSound | None:
    sound = NSSound.soundNamed_(name)
    if sound is None:
        log.warning("system sound %r not found; that cue is disabled", name)
        return None
    sound.setVolume_(volume)
    return sound


def _play(sound: NSSound | None) -> None:
    if sound is None:
        return

    def go() -> None:
        if sound.isPlaying():
            sound.stop()  # restart so rapid presses still tick
        sound.play()

    AppHelper.callAfter(go)


class SoundCues:
    def __init__(
        self, start_name: str, stop_name: str, volume: float, enabled: bool
    ) -> None:
        self.enabled = enabled
        self._start = _load(start_name, volume)
        self._stop = _load(stop_name, volume)

    def start(self) -> None:
        if self.enabled:
            _play(self._start)

    def stop(self) -> None:
        if self.enabled:
            _play(self._stop)
