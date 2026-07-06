"""Microphone capture: 16 kHz mono float32, matching Whisper's expected input."""

import logging

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
MIN_CLIP_SECONDS = 0.3  # shorter than this is an accidental tap, not speech


class Recorder:
    def __init__(self) -> None:
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._on_audio,
        )
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status) -> None:
        if status:
            log.warning("audio stream status: %s", status)
        self._frames.append(indata.copy())

    def stop(self) -> np.ndarray | None:
        """Stop capturing and return the clip, or None if it was too short."""
        if self._stream is None:
            return None
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if not self._frames:
            return None
        audio = np.concatenate(self._frames)[:, 0]
        if len(audio) < int(MIN_CLIP_SECONDS * SAMPLE_RATE):
            log.info("clip too short (%.2fs), discarding", len(audio) / SAMPLE_RATE)
            return None
        return audio
