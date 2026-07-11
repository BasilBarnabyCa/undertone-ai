"""Unit tests for chunked long-hold processing.

chunk_seconds is set to a large number (999) in every test: LongSession only
loops when its background thread's Event.wait() times out, and .set() (called
by stop()/finish()) makes that wait return immediately regardless of the
timeout value — so these tests never actually wait 999 seconds, they just
never rely on the real periodic loop firing on its own.
"""

import numpy as np

from undertone import long_session
from undertone.long_session import SAMPLE_RATE, LongSession


def _audio(seconds: float, value: float = 0.1) -> np.ndarray:
    return np.full(int(seconds * SAMPLE_RATE), value, dtype=np.float32)


class _FakeRecorder:
    """Not exercised directly in these tests (chunks are fed via _process_chunk
    or the constructor's tail_audio), but required to satisfy the interface."""

    def take_pending(self):
        return None


class _FakeTranscriber:
    def __init__(self):
        self.calls = []  # initial_prompt seen on each call

    def transcribe(self, audio, initial_prompt=None):
        self.calls.append(initial_prompt)
        return f"chunk {len(self.calls)}"


def _session(**overrides):
    kwargs = dict(
        recorder=_FakeRecorder(),
        transcriber=_FakeTranscriber(),
        chunk_seconds=999,
        cleanup_enabled=False,
        ollama_model="m",
        ollama_url="u",
        cleanup_timeout=1.0,
    )
    kwargs.update(overrides)
    return LongSession(**kwargs)


class TestProcessChunk:
    def test_skips_none_audio(self):
        session = _session()
        session._process_chunk(None)
        assert session._chunks == []

    def test_skips_too_short_audio(self):
        session = _session()
        session._process_chunk(_audio(0.1))
        assert session._chunks == []

    def test_appends_transcribed_text(self):
        session = _session()
        session._process_chunk(_audio(2.0))
        assert session._chunks == ["chunk 1"]

    def test_threads_previous_chunk_as_initial_prompt(self):
        fake_tr = _FakeTranscriber()
        session = _session(transcriber=fake_tr)
        session._process_chunk(_audio(2.0))
        session._process_chunk(_audio(2.0))
        assert fake_tr.calls == [None, "chunk 1"]

    def test_applies_cleanup_when_enabled(self, monkeypatch):
        monkeypatch.setattr(
            long_session.cleanup, "clean", lambda text, model, url, timeout: text.upper()
        )
        session = _session(cleanup_enabled=True)
        session._process_chunk(_audio(2.0))
        assert session._chunks == ["CHUNK 1"]

    def test_skips_cleanup_when_disabled(self, monkeypatch):
        monkeypatch.setattr(
            long_session.cleanup,
            "clean",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
        )
        session = _session(cleanup_enabled=False)
        session._process_chunk(_audio(2.0))
        assert session._chunks == ["chunk 1"]

    def test_swallows_exceptions_without_recording_a_chunk(self):
        class _Boom:
            def transcribe(self, audio, initial_prompt=None):
                raise RuntimeError("boom")

        session = _session(transcriber=_Boom())
        session._process_chunk(_audio(2.0))  # must not raise
        assert session._chunks == []


class TestFinish:
    def test_returns_none_with_no_chunks_and_no_tail(self):
        session = _session()
        session.start()
        assert session.finish(None) is None

    def test_processes_the_tail_and_joins_with_prior_chunks(self):
        session = _session()
        session.start()
        session._chunks = ["Hello.", "World."]
        result = session.finish(_audio(2.0))
        assert result == "Hello. World. chunk 1"


class TestStop:
    def test_does_not_process_a_final_chunk(self):
        fake_tr = _FakeTranscriber()
        session = _session(transcriber=fake_tr)
        session.start()
        session.stop()
        assert fake_tr.calls == []
        assert session._chunks == []
