"""Accidental-fire safeguards: clip gates and hallucination filtering."""

import numpy as np

from undertone.recorder import SAMPLE_RATE, clip_ok
from undertone.transcriber import looks_hallucinated


def _tone(seconds: float, amplitude: float) -> np.ndarray:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


class TestClipOk:
    def test_rejects_accidental_tap(self):
        assert not clip_ok(_tone(0.1, 0.1))

    def test_rejects_silent_hold(self):
        assert not clip_ok(np.zeros(2 * SAMPLE_RATE, dtype=np.float32))

    def test_rejects_ambient_noise(self):
        noise = np.random.default_rng(0).normal(0, 0.001, 2 * SAMPLE_RATE)
        assert not clip_ok(noise.astype(np.float32))

    def test_accepts_speech_level_audio(self):
        assert clip_ok(_tone(1.0, 0.05))


class TestLooksHallucinated:
    def test_catches_whisper_silence_outputs(self):
        assert looks_hallucinated("Thank you.")
        assert looks_hallucinated(" thanks for watching! ")
        assert looks_hallucinated("you")
        assert looks_hallucinated("Bye.")

    def test_keeps_real_sentences(self):
        assert not looks_hallucinated("Thank you for the update, see you Thursday.")
        assert not looks_hallucinated("Move the meeting to Thursday.")
        assert not looks_hallucinated("bye for now, talk soon")
