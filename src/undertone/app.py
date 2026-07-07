"""Menu bar app: wires hotkey → recorder → transcriber → cleanup → injector.

State machine lives here. The hotkey listener thread only flips state; all
heavy work (transcription, LLM cleanup, paste) happens on a worker thread so
key events are never blocked.
"""

import logging
import threading

import rumps

from . import cleanup, config, icons, injector
from .hotkey import HoldHotkey
from .hud import RecordingHUD
from .recorder import Recorder
from .transcriber import Transcriber

log = logging.getLogger(__name__)

WARN_GLYPH = "⚠️"  # shown as text when warm-up fails (no usable icon state)

PERMISSIONS_NOTE = """\
undertone needs three permissions (System Settings → Privacy & Security):
  • Microphone         — to hear you
  • Input Monitoring   — to see the hold-to-talk key anywhere
  • Accessibility      — to paste the transcript into other apps
Grant them to your terminal app (it hosts this process), then relaunch.
"""


class UndertoneApp(rumps.App):
    def __init__(self) -> None:
        # The mark is the menu bar icon: full-colour while running, dimmed while
        # warming up or busy. Start dimmed until warm-up finishes.
        active, muted = icons.ensure_icons()
        super().__init__("Undertone", icon=muted, template=False, quit_button="Quit")
        self._icon_active, self._icon_muted = active, muted
        self.cfg = config.load()
        self.recorder = Recorder()
        self.transcriber = Transcriber(self.cfg.whisper_model, self.cfg.language)
        self.hud = RecordingHUD()
        self._busy = threading.Lock()

        self.cleanup_item = rumps.MenuItem("LLM cleanup (Ollama)", callback=self._toggle_cleanup)
        self.cleanup_item.state = self.cfg.cleanup_enabled
        self.menu = [
            self.cleanup_item,
            rumps.MenuItem(f"Hotkey: hold {self.cfg.hotkey}", callback=None),
            rumps.MenuItem(f"Model: {self.cfg.whisper_model.split('/')[-1]}", callback=None),
            None,
        ]

        self.hotkey = HoldHotkey(
            self.cfg.hotkey, self._on_key_down, self._on_key_up, self._on_key_cancel
        )
        threading.Thread(target=self._warm_up, daemon=True).start()

    # -- menu bar state ------------------------------------------------------

    def _show_mark(self, active: bool) -> None:
        """Display the mark icon (dropping any warning glyph)."""
        self.title = None
        self.icon = self._icon_active if active else self._icon_muted

    def _show_warning(self) -> None:
        self.icon = None
        self.title = WARN_GLYPH

    # -- startup ------------------------------------------------------------

    def _warm_up(self) -> None:
        try:
            self.transcriber.warm_up()
        except Exception:
            log.exception("whisper warm-up failed")
            self._show_warning()
            return
        if self.cfg.cleanup_enabled:
            cleanup.warm_up(self.cfg.ollama_model, self.cfg.ollama_url)
        self.hotkey.start()
        if not injector.is_trusted():
            log.error(
                "ACCESSIBILITY NOT GRANTED — dictation will transcribe but cannot "
                "paste (transcripts will be left on the clipboard instead). Fix: "
                "System Settings → Privacy & Security → Accessibility → enable "
                "your terminal app, then fully quit the terminal and relaunch."
            )
            self._show_warning()
            return
        self._show_mark(active=True)
        log.info("ready — hold %s to dictate", self.cfg.hotkey)

    # -- hotkey callbacks (listener thread) ----------------------------------

    def _on_key_down(self) -> None:
        if self._busy.locked():
            return
        # The HUD is the live "listening" indicator; the menu bar mark stays lit.
        self.hud.show()
        self.recorder.start()

    def _on_key_up(self) -> None:
        if not self.recorder.recording:
            return
        self.hud.hide()
        threading.Thread(target=self._process, daemon=True).start()

    def _on_key_cancel(self) -> None:
        self.hud.hide()
        self.recorder.cancel()
        self._show_mark(active=True)

    # -- pipeline (worker thread) --------------------------------------------

    def _process(self) -> None:
        with self._busy:
            self._show_mark(active=False)  # dimmed while transcribing/cleaning
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
                self._show_mark(active=True)

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
    UndertoneApp().run()


if __name__ == "__main__":
    main()
