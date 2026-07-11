"""Chunked processing for long holds.

Short dictation (the common case — a sentence or two) is transcribed and
cleaned in one shot after release; that fast path is untouched by this file.
But a long hold (a recorded conversation, a multi-minute monologue) pays two
costs that both scale with length if left until release: Whisper's transcribe
time, and Ollama cleanup's fixed timeout — which a multi-minute transcript
will reliably blow past (confirmed in the log: every multi-minute clip's
cleanup call timed out and silently fell back to raw text, meaning cleanup
never actually ran on anything long).

LongSession runs in the background once a hold crosses `chunk_seconds`
(app.py only creates one past that point — short holds never pay this cost).
Every interval it drains whatever the recorder has captured so far via
`Recorder.take_pending()`, transcribes and (optionally) cleans just that
slice, and appends the result. `finish()` stops the loop and processes the
final partial slice once the recorder itself has been closed. Net effect:
release-to-paste latency is bounded to roughly one slice's cost instead of
the whole recording's, and each cleanup call gets a chunk small enough to
actually finish inside its timeout.

Trade-off carried over from the (reverted, see ROADMAP.md) short-clip
streaming experiment: each chunk is transcribed independently, so a sentence
split across a chunk boundary can lose a little context. `initial_prompt`
threads the previous chunk's raw transcript in to reduce this — it isn't a
full fix, and hasn't been validated yet against a real long recording.
"""

import logging
import threading

import numpy as np

from . import cleanup
from .recorder import SAMPLE_RATE

log = logging.getLogger(__name__)

MIN_CHUNK_SECONDS = 1.0  # slices shorter than this aren't worth a Whisper call


class LongSession:
    def __init__(
        self,
        recorder,
        transcriber,
        *,
        chunk_seconds: float,
        cleanup_enabled: bool,
        ollama_model: str,
        ollama_url: str,
        cleanup_timeout: float,
    ) -> None:
        self._recorder = recorder
        self._transcriber = transcriber
        self._chunk_seconds = chunk_seconds
        self._cleanup_enabled = cleanup_enabled
        self._ollama_model = ollama_model
        self._ollama_url = ollama_url
        self._cleanup_timeout = cleanup_timeout
        self._chunks: list[str] = []
        self._raw_tail = ""
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(self._chunk_seconds):
            self._process_chunk(self._recorder.take_pending())

    def _process_chunk(self, audio: np.ndarray | None) -> None:
        if audio is None or len(audio) < MIN_CHUNK_SECONDS * SAMPLE_RATE:
            return
        try:
            text = self._transcriber.transcribe(audio, initial_prompt=self._raw_tail or None)
            if not text:
                return
            self._raw_tail = text
            if self._cleanup_enabled:
                text = cleanup.clean(
                    text, self._ollama_model, self._ollama_url, self._cleanup_timeout
                )
            with self._lock:
                self._chunks.append(text)
        except Exception:
            # One bad slice shouldn't cost the rest of a long recording.
            log.exception("long-session chunk failed, dropping this slice")

    def stop(self) -> None:
        """Abort without processing a final slice (the hold was cancelled)."""
        self._stop_event.set()
        self._thread.join()

    def finish(self, tail_audio: np.ndarray | None) -> str | None:
        """Stop the periodic loop and process the final partial slice."""
        self._stop_event.set()
        self._thread.join()
        self._process_chunk(tail_audio)
        with self._lock:
            return " ".join(self._chunks) or None
