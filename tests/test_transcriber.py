"""Unit tests for initial_prompt threading (no real mlx_whisper call)."""

import numpy as np

from undertone import transcriber as t


def _audio(seconds: float = 0.1) -> np.ndarray:
    return np.zeros(int(seconds * t.SAMPLE_RATE), dtype=np.float32)


def test_initial_prompt_is_forwarded(monkeypatch):
    seen = {}

    def fake_transcribe(audio, **kwargs):
        seen.update(kwargs)
        return {"text": "hello"}

    monkeypatch.setattr(t.mlx_whisper, "transcribe", fake_transcribe)
    tr = t.Transcriber("some/model", "en")
    tr.transcribe(_audio(), initial_prompt="prior context")
    assert seen["initial_prompt"] == "prior context"


def test_no_initial_prompt_key_when_not_given(monkeypatch):
    seen = {}

    def fake_transcribe(audio, **kwargs):
        seen.update(kwargs)
        return {"text": "hello"}

    monkeypatch.setattr(t.mlx_whisper, "transcribe", fake_transcribe)
    tr = t.Transcriber("some/model", "en")
    tr.transcribe(_audio())
    assert "initial_prompt" not in seen


def test_empty_initial_prompt_is_not_forwarded(monkeypatch):
    """An empty string ("no context yet") shouldn't be passed through either."""
    seen = {}

    def fake_transcribe(audio, **kwargs):
        seen.update(kwargs)
        return {"text": "hello"}

    monkeypatch.setattr(t.mlx_whisper, "transcribe", fake_transcribe)
    tr = t.Transcriber("some/model", "en")
    tr.transcribe(_audio(), initial_prompt="")
    assert "initial_prompt" not in seen
