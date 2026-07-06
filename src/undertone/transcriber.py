"""On-device speech-to-text via mlx-whisper."""

import logging
import time

import mlx_whisper
import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16_000


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

    def transcribe(self, audio: np.ndarray) -> str:
        t0 = time.monotonic()
        result = mlx_whisper.transcribe(
            audio, path_or_hf_repo=self.model, language=self.language
        )
        text = result["text"].strip()
        log.info(
            "transcribed %.1fs of audio in %.2fs: %r",
            len(audio) / SAMPLE_RATE,
            time.monotonic() - t0,
            text,
        )
        return text
