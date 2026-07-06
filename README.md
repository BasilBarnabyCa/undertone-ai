# whisper-flow-clone

A local, free Wispr Flow clone for macOS. Hold a hotkey anywhere, speak, release — your words are transcribed on-device with Whisper, optionally polished by a local LLM (Ollama), and typed into whatever app has focus. No cloud, no subscription, nothing leaves your machine.

## How it works

1. **Hold the hotkey** (Right Option by default) — audio starts recording from your mic.
2. **Release** — the clip is transcribed on-device by `mlx-whisper` (Apple Silicon optimized).
3. **Optional cleanup** — a small local LLM via Ollama removes filler words and fixes punctuation (toggle in the menu bar).
4. **The text is pasted** into the frontmost app via a simulated ⌘V (your clipboard is restored afterwards).

## Quick start

```bash
uv sync
uv run whisperflow
```

First run downloads the Whisper model (~1.6 GB) and will prompt for **Microphone**, **Accessibility**, and **Input Monitoring** permissions in System Settings.

For LLM cleanup: install [Ollama](https://ollama.com) (`brew install ollama`), then `ollama pull llama3.2:3b`.

## Requirements

- Apple Silicon Mac (built on an M4 Pro)
- Python 3.13+, [uv](https://docs.astral.sh/uv/)
- Ollama (optional, for the cleanup pass)
