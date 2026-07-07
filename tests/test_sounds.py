"""Sound cue gating: playback happens only when enabled; bad names disable safely."""

import undertone.sounds as sounds
from undertone.sounds import SoundCues, _load


def test_load_missing_name_returns_none():
    assert _load("NoSuchSound__xyz", 0.5) is None


def test_enabled_gates_playback(monkeypatch):
    monkeypatch.setattr(sounds, "_load", lambda name, vol: f"snd:{name}")
    played: list[str] = []
    monkeypatch.setattr(sounds, "_play", played.append)

    cues = SoundCues("Tink", "Pop", 0.5, enabled=False)
    cues.start()
    cues.stop()
    assert played == []  # off by default: silent

    cues.enabled = True
    cues.start()
    cues.stop()
    assert played == ["snd:Tink", "snd:Pop"]  # toggled on: start then stop cue
