"""Menu bar app: wires hotkey → recorder → transcriber → cleanup → injector.

State machine lives here. The hotkey listener thread only flips state; all
heavy work (transcription, LLM cleanup, paste) happens on a worker thread so
key events are never blocked.
"""

import logging
import threading

import rumps

from . import cleanup, config, injector
from .hotkey import HoldHotkey
from .recorder import Recorder
from .transcriber import Transcriber

log = logging.getLogger(__name__)

ICON_IDLE = "🎤"
ICON_RECORDING = "🔴"
ICON_WORKING = "⏳"
ICON_LOADING = "⌛"

PERMISSIONS_NOTE = """\
whisperflow needs three permissions (System Settings → Privacy & Security):
  • Microphone         — to hear you
  • Input Monitoring   — to see the hold-to-talk key anywhere
  • Accessibility      — to paste the transcript into other apps
Grant them to your terminal app (it hosts this process), then relaunch.
"""


class WhisperFlowApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(ICON_LOADING, quit_button="Quit")
        self.cfg = config.load()
        self.recorder = Recorder()
        self.transcriber = Transcriber(self.cfg.whisper_model, self.cfg.language)
        self._busy = threading.Lock()

        self.cleanup_item = rumps.MenuItem("LLM cleanup (Ollama)", callback=self._toggle_cleanup)
        self.cleanup_item.state = self.cfg.cleanup_enabled
        self.menu = [
            self.cleanup_item,
            rumps.MenuItem(f"Hotkey: hold {self.cfg.hotkey}", callback=None),
            rumps.MenuItem(f"Model: {self.cfg.whisper_model.split('/')[-1]}", callback=None),
            None,
        ]

        self.hotkey = HoldHotkey(self.cfg.hotkey, self._on_key_down, self._on_key_up)
        threading.Thread(target=self._warm_up, daemon=True).start()

    # -- startup ------------------------------------------------------------

    def _warm_up(self) -> None:
        try:
            self.transcriber.warm_up()
        except Exception:
            log.exception("whisper warm-up failed")
            self.title = "⚠️"
            return
        if self.cfg.cleanup_enabled:
            cleanup.warm_up(self.cfg.ollama_model, self.cfg.ollama_url)
        self.hotkey.start()
        self.title = ICON_IDLE
        log.info("ready — hold %s to dictate", self.cfg.hotkey)

    # -- hotkey callbacks (listener thread) ----------------------------------

    def _on_key_down(self) -> None:
        if self._busy.locked():
            return
        self.title = ICON_RECORDING
        self.recorder.start()

    def _on_key_up(self) -> None:
        if not self.recorder.recording:
            return
        threading.Thread(target=self._process, daemon=True).start()

    # -- pipeline (worker thread) --------------------------------------------

    def _process(self) -> None:
        with self._busy:
            self.title = ICON_WORKING
            try:
                audio = self.recorder.stop()
                if audio is None:
                    return
                text = self.transcriber.transcribe(audio)
                if not text:
                    return
                if self.cleanup_item.state:
                    text = cleanup.clean(
                        text,
                        self.cfg.ollama_model,
                        self.cfg.ollama_url,
                        self.cfg.cleanup_timeout,
                    )
                injector.paste_text(text)
            except Exception:
                log.exception("dictation pipeline failed")
            finally:
                self.title = ICON_IDLE

    # -- menu ----------------------------------------------------------------

    def _toggle_cleanup(self, item: rumps.MenuItem) -> None:
        item.state = not item.state
        log.info("LLM cleanup %s", "on" if item.state else "off")


def main() -> None:
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(config.LOG_PATH), logging.StreamHandler()],
    )
    print(PERMISSIONS_NOTE)
    WhisperFlowApp().run()


if __name__ == "__main__":
    main()
