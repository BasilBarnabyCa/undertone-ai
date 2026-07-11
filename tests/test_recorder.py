"""Unit tests for the take_pending/close/stop primitives (no real audio device)."""

import numpy as np

from undertone.recorder import SAMPLE_RATE, Recorder


class _FakeStream:
    """Duck-types sd.InputStream's stop()/close() without touching hardware."""

    def __init__(self) -> None:
        self.stopped = False
        self.closed = False

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def _chunk(seconds: float, value: float = 0.1) -> np.ndarray:
    return np.full((int(seconds * SAMPLE_RATE), 1), value, dtype=np.float32)


class TestTakePending:
    def test_returns_none_when_empty(self):
        assert Recorder().take_pending() is None

    def test_drains_and_clears(self):
        r = Recorder()
        r._frames = [_chunk(0.5), _chunk(0.5)]
        audio = r.take_pending()
        assert audio is not None
        assert len(audio) == SAMPLE_RATE
        assert r.take_pending() is None  # already drained

    def test_accumulates_only_since_last_call(self):
        r = Recorder()
        r._frames.append(_chunk(0.2))
        first = r.take_pending()
        r._frames.append(_chunk(0.3))
        second = r.take_pending()
        assert len(first) == int(0.2 * SAMPLE_RATE)
        assert len(second) == int(0.3 * SAMPLE_RATE)


class TestClose:
    def test_returns_none_without_a_stream(self):
        assert Recorder().close() is None

    def test_stops_and_drains_ungated(self):
        r = Recorder()
        r._stream = _FakeStream()
        r._frames = [_chunk(0.1)]  # below MIN_CLIP_SECONDS — close() doesn't gate
        audio = r.close()
        assert audio is not None
        assert len(audio) == int(0.1 * SAMPLE_RATE)
        assert not r.recording


class TestStop:
    def test_gates_a_short_clip_close_would_have_returned(self):
        r = Recorder()
        r._stream = _FakeStream()
        r._frames = [_chunk(0.1)]  # below MIN_CLIP_SECONDS
        assert r.stop() is None

    def test_accepts_a_real_clip(self):
        r = Recorder()
        r._stream = _FakeStream()
        r._frames = [_chunk(1.0)]
        audio = r.stop()
        assert audio is not None
        assert len(audio) == SAMPLE_RATE
