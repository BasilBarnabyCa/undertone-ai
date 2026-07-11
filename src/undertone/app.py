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
from .long_session import LongSession
from .recorder import Recorder
from .sounds import SoundCues
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
        # The mark is the menu bar icon: full opacity while running, dimmed while
        # warming up or busy. Start dimmed until warm-up finishes. template=True
        # lets macOS auto-recolor it for light/dark menu bars and selection.
        active, muted = icons.ensure_icons()
        super().__init__("Undertone", icon=muted, template=True, quit_button="Quit")
        self._icon_active, self._icon_muted = active, muted
        self.cfg = config.load()
        self.recorder = Recorder()
        self.transcriber = Transcriber(self.cfg.whisper_model, self.cfg.language)
        self.hud = RecordingHUD()
        self.sounds = SoundCues(
            self.cfg.sound_start,
            self.cfg.sound_stop,
            self.cfg.sound_volume,
            self.cfg.sounds_enabled,
        )
        self._busy = threading.Lock()
        # Set once a hold crosses cfg.chunk_seconds (see _promote_to_long_session).
        # None means "still a normal short hold" — the fast path is unaffected.
        self._long_session: LongSession | None = None
        self._chunk_timer: threading.Timer | None = None

        self.cleanup_item = rumps.MenuItem("LLM cleanup (Ollama)", callback=self._toggle_cleanup)
        self.cleanup_item.state = self.cfg.cleanup_enabled
        self.sounds_item = rumps.MenuItem("Sound cues", callback=self._toggle_sounds)
        self.sounds_item.state = self.cfg.sounds_enabled
        self.menu = [
            self.cleanup_item,
            self.sounds_item,
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
        self.sounds.start()
        try:
            self.recorder.start()
        except Exception:
            # sd.InputStream can fail to open (e.g. the input device is mid
            # renegotiation). If this isn't caught, recorder.recording stays
            # False, so _on_key_up later no-ops and never hides the HUD —
            # the app looks "stuck listening" while capturing nothing.
            log.exception("failed to start recording")
            self.hud.hide()
            self.sounds.stop()
            self._show_warning()
            return
        self._long_session = None
        self._chunk_timer = threading.Timer(self.cfg.chunk_seconds, self._promote_to_long_session)
        self._chunk_timer.daemon = True
        self._chunk_timer.start()

    def _promote_to_long_session(self) -> None:
        # Fires on its own timer thread once a hold crosses chunk_seconds.
        # Short dictation never reaches this — only genuinely long holds pay
        # for chunked processing.
        if not self.recorder.recording:
            return
        log.info("hold past %.0fs — switching to chunked long-session processing", self.cfg.chunk_seconds)
        self._long_session = LongSession(
            self.recorder,
            self.transcriber,
            chunk_seconds=self.cfg.chunk_seconds,
            cleanup_enabled=self.cleanup_item.state,
            ollama_model=self.cfg.ollama_model,
            ollama_url=self.cfg.ollama_url,
            cleanup_timeout=self.cfg.cleanup_timeout,
        )
        self._long_session.start()

    def _on_key_up(self) -> None:
        if not self.recorder.recording:
            return
        if self._chunk_timer is not None:
            self._chunk_timer.cancel()
        self.hud.hide()
        self.sounds.stop()
        threading.Thread(target=self._process, daemon=True).start()

    def _on_key_cancel(self) -> None:
        if self._chunk_timer is not None:
            self._chunk_timer.cancel()
        self.hud.hide()
        self.recorder.cancel()
        self._show_mark(active=True)
        session, self._long_session = self._long_session, None
        if session is not None:
            # Abort in the background — a session mid-chunk can take a few
            # seconds to unwind, and the hotkey listener thread must not block.
            threading.Thread(target=session.stop, daemon=True).start()

    # -- pipeline (worker thread) --------------------------------------------

    def _process(self) -> None:
        with self._busy:
            self._show_mark(active=False)  # dimmed while transcribing/cleaning
            try:
                session, self._long_session = self._long_session, None
                if session is not None:
                    # Long hold: most of it was already transcribed+cleaned in
                    # the background. Only the trailing partial slice is left,
                    # so tail latency here is bounded to ~one chunk, not the
                    # whole recording. close() is ungated (no clip_ok) — the
                    # hold already proved itself real speech via earlier chunks.
                    tail = self.recorder.close()
                    text = session.finish(tail)
                else:
                    audio = self.recorder.stop()
                    # Narrow race: the promotion timer could have fired in the
                    # same instant as key-up (already running when cancel()
                    # was called doesn't stop it). If so, a session exists
                    # that nobody will ever finish() — stop it rather than
                    # leak its background thread.
                    late_session, self._long_session = self._long_session, None
                    if late_session is not None:
                        late_session.stop()
                    if audio is None:
                        return
                    text = self.transcriber.transcribe(audio)
                    if text and self.cleanup_item.state:
                        text = cleanup.clean(
                            text,
                            self.cfg.ollama_model,
                            self.cfg.ollama_url,
                            self.cfg.cleanup_timeout,
                        )
                if not text:
                    return
                injector.paste_text(text)
            except Exception:
                log.exception("dictation pipeline failed")
            finally:
                self._show_mark(active=True)

    # -- menu ----------------------------------------------------------------

    def _toggle_cleanup(self, item: rumps.MenuItem) -> None:
        item.state = not item.state
        log.info("LLM cleanup %s", "on" if item.state else "off")

    def _toggle_sounds(self, item: rumps.MenuItem) -> None:
        item.state = not item.state
        self.sounds.enabled = bool(item.state)
        log.info("sound cues %s", "on" if item.state else "off")


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
