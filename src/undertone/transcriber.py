"""On-device speech-to-text via mlx-whisper."""

import logging
import time

import mlx_whisper
import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16_000

# Whisper's well-known outputs on silence/noise-only audio. A transcript that
# is exactly one of these almost certainly wasn't speech.
HALLUCINATIONS = {
    "thank you",
    "thanks",
    "thank you for watching",
    "thanks for watching",
    "you",
    "bye",
    "please subscribe",
    "please subscribe to my channel",
}


def looks_hallucinated(text: str) -> bool:
    return text.lower().strip(" .,!?") in HALLUCINATIONS


class Transcriber:
    def __init__(self, model: str, language: str = "en") -> None:
        self.model = model
        self.language = language or None

    def warm_up(self) -> None:
        """Run a dummy transcription so the first real one doesn't pay model-load cost."""
        t0 = time.monotonic()
        mlx_whisper.transcribe(
            np.zeros(SAMPLE_RATE, dtype=np.float32), path_or_hf_repo=self.model
        )
        log.info("model %s warm in %.1fs", self.model, time.monotonic() - t0)

    def transcribe(self, audio: np.ndarray, initial_prompt: str | None = None) -> str:
        t0 = time.monotonic()
        kwargs = {"path_or_hf_repo": self.model, "language": self.language}
        if initial_prompt:
            # Threads the previous chunk's raw transcript in as context for
            # long-hold chunking (long_session.py), so a chunk boundary that
            # splits a sentence has some idea what came right before it.
            kwargs["initial_prompt"] = initial_prompt
        result = mlx_whisper.transcribe(audio, **kwargs)
        text = result["text"].strip()
        if looks_hallucinated(text):
            log.info("dropping likely hallucination: %r", text)
            text = ""
        log.info(
            "transcribed %.1fs of audio in %.2fs: %r",
            len(audio) / SAMPLE_RATE,
            time.monotonic() - t0,
            text,
        )
        return text
