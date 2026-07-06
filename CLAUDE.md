# CLAUDE.md — undertone

## What this is
A local Wispr Flow clone for macOS: Python menu bar app, global hold-to-talk hotkey, on-device Whisper transcription (mlx-whisper), optional Ollama LLM cleanup pass, pastes the result into the focused app. Built by and for Basil.

## Ownership
Self-owned personal project. Safe to publish, reuse, and reference by name.

## Stack & key commands
- Python 3.13, managed with `uv` (deps in `pyproject.toml`)
- `uv sync` — install/update deps
- `uv run undertone` — run the menu bar app
- `uv run pytest` — tests
- Transcription: `mlx-whisper` (Apple Silicon). Cleanup: Ollama HTTP API (`llama3.2:3b`).
- Audio: `sounddevice`. Menu bar: `rumps`. Hotkey: `pynput`. Paste: `pyobjc` (NSPasteboard + CGEvent ⌘V).

## Conventions
- Commits follow COMMIT_CONVENTIONS.md (conventional commits).
- Package lives in `src/undertone/`; one module per concern (recorder, transcriber, cleanup, injector, hotkey, config, app).
- Config is a user-editable file at `~/.config/undertone/config.toml`; defaults in `config.py`.

## Session start
Read PLAN.md (the working plan) and DEV_JOURNAL.md (session log) before doing anything.

## Boundaries / gotchas
- macOS permissions (Microphone, Accessibility, Input Monitoring) can only be granted by Basil in System Settings — code can't self-grant. Surface clear instructions when they're missing.
- Never send audio or transcripts to any network service other than localhost Ollama.
- Clipboard must always be restored after paste-injection, even on error paths.
