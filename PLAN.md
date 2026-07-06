# Plan — undertone

> Self-contained: a fresh session can execute this without other context.

## Context (why this exists, for whom)
Basil wants Wispr Flow's system-wide voice dictation without the subscription or the cloud: hold a hotkey in any macOS app, speak, release, and clean text appears where the cursor is. Everything runs locally on his M4 Pro — Whisper for speech-to-text, a small Ollama model for transcript polish. Personal, self-owned project.

## Goal (the one-sentence definition of done)
Holding Right Option anywhere on macOS records speech and, on release, types an accurate, cleaned-up transcript into the focused app within ~2 seconds for a typical sentence — fully offline.

## Tasks (ordered, concrete)
1. **Environment**: install `uv`, `ollama`, `ffmpeg` via Homebrew; `ollama pull llama3.2:3b`; create `pyproject.toml` with deps (`mlx-whisper`, `sounddevice`, `numpy`, `rumps`, `pynput`, `pyobjc`, `requests`) and `src/undertone/` package with a `undertone` entry point.
2. **Transcriber** (`transcriber.py`): wrap `mlx-whisper` with `mlx-community/whisper-large-v3-turbo`; accept a 16 kHz mono float32 numpy array, return text. Pre-warm the model at app start. Verify standalone with a test WAV.
3. **Recorder** (`recorder.py`): `sounddevice` InputStream, 16 kHz mono; `start()`/`stop() -> np.ndarray`; discard clips shorter than ~0.3 s.
4. **Hotkey** (`hotkey.py`): `pynput` global listener for hold-Right-Option → on_press start, on_release stop. Key configurable.
5. **Injector** (`injector.py`): save NSPasteboard contents → write transcript → CGEvent ⌘V → restore clipboard (always, even on error).
6. **Cleanup** (`cleanup.py`): POST to localhost Ollama (`llama3.2:3b`), prompt: fix punctuation/casing, drop filler words, never add or change content; return raw transcript on any failure or timeout (2 s cap).
7. **Menu bar app** (`app.py`, `rumps`): mic icon that changes state while recording/transcribing; toggles for LLM cleanup and model choice; Quit. Wire all modules; log to `~/.config/undertone/undertone.log`.
8. **Config** (`config.py`): TOML at `~/.config/undertone/config.toml` — hotkey, whisper model, ollama model, cleanup on/off.
9. **Permissions UX**: detect missing Microphone/Accessibility/Input Monitoring permissions and print/notify clear System Settings instructions.
10. **End-to-end verify**: dictate into TextEdit, Slack-style textarea in a browser, and a terminal; measure latency; tune (e.g. swap to `distil-whisper` or smaller Ollama model if slow).

## Acceptance criteria (checkboxes, verifiable)
- [ ] `uv run undertone` launches a menu bar app with no terminal errors
- [ ] Hold-Right-Option → speak → release types the transcript into TextEdit at the cursor
- [ ] Works in at least 3 different apps (native, browser, terminal)
- [ ] Cleanup toggle changes output (fillers removed when on; raw when off)
- [ ] Ollama down/killed → raw transcript still delivered (graceful fallback)
- [ ] Clipboard contents survive a dictation round-trip
- [ ] A ~10-word sentence lands in ≤ ~2 s on the M4 Pro
- [ ] Nothing is written outside the project dir and `~/.config/undertone/`

## Hard gates (decisions/credentials only the user can provide)
- Granting Microphone, Accessibility, and Input Monitoring permissions in System Settings when prompted.
- Confirming Right Option as the hotkey feels right in daily use (easy to change in config).

## Out of scope (explicit non-goals)
- Windows/Linux support
- Real-time streaming transcription (word-by-word as you speak) — v1 is record-then-transcribe
- Custom vocabulary / speaker adaptation, multi-language auto-detect UI
- Packaging as a signed .app / DMG (runs via `uv run` for now)
- Any cloud API usage
