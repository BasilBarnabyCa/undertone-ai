# Dev Journal — undertone

> One entry per session, newest first. The top entry's "Next steps" is the handoff.

## 2026-07-07 — v1 pipeline built, named, safeguarded, and working end-to-end

**The app works.** Hold right Option anywhere → speak → release → transcript is cleaned by Ollama and pasted into the focused app. Verified live in Terminal and Notes.

### Done

1. **Built the full v1 pipeline** (d56a4fa, 1610f47): menu bar app (rumps), global hold-to-talk hotkey (pynput, right Option), 16 kHz mic capture (sounddevice), on-device transcription (mlx-whisper, `whisper-large-v3-turbo`), optional LLM cleanup via localhost Ollama (`llama3.2:3b`, fail-open to raw transcript), paste injection (NSPasteboard swap + synthetic ⌘V).
2. **Renamed WhisperFlow → undertone** (5fd463c) after checking name availability. GitHub remote: `BasilBarnabyCa/undertone-ai`, branch `main`.
3. **Wrote ROADMAP.md** (2ecf169) — gap analysis vs Wispr Flow, ordered v0.2 → v1.0.
4. **Accidental-fire safeguards** (ccc253f): min clip length (0.3 s), RMS silence gate, Whisper hallucination filter ("Thank you." etc.), cancel-on-other-key while hotkey held. 6 unit tests in `tests/test_guards.py`, all passing.
5. **Solved the paste-into-Notes failure** (**uncommitted**): root cause was missing Accessibility permission — macOS drops synthetic ⌘V silently. Fixed by granting the terminal app Accessibility and fully restarting it. Hardened the code:
   - `injector.py`: `is_trusted()` (`AXIsProcessTrusted` via ctypes); when untrusted, the transcript is **left on the clipboard** as fallback delivery instead of being wiped by the restore. `paste_text()` now returns a bool.
   - `app.py`: loud `ACCESSIBILITY NOT GRANTED` startup error with fix steps; menu bar shows ⚠️ instead of 🎤 when untrusted.

### Known issues / observations

- **Cleanup prompt is slightly too aggressive** — dropped "Testing" from "Testing undertone…" and "I think" in an earlier bench test. Tuning with an eval set is the v0.3 roadmap item; the menu toggle disables cleanup meanwhile.
- **Esc isn't truly captured** — pynput is passive, so Esc cancels dictation but still reaches the frontmost app. Real capture needs a CGEventTap (bundled with the v0.4 chord-hotkey work).
- **Permissions attach to the terminal app** and only apply to freshly launched processes — after any grant, ⌘Q the terminal and reopen. The packaged .app (v1.0) removes this papercut.

### Next steps, in order

1. **Commit the uncommitted work**: `injector.py` + `app.py` accessibility hardening (`/git-commit-push`). Include this file.
2. **Finish v1 acceptance criteria** (PLAN.md): dictation verified in Terminal ✅ and Notes ✅ — still to check: a browser text field, clipboard contents survive a paste round-trip, latency feels ≤ ~2 s, and the Ollama-down fallback (stop Ollama, dictate, expect raw transcript).
3. **Rename the project folder** (outside any session): `mv ~/dev/ai/whisper-flow-clone ~/dev/ai/undertone`.
4. **Start v0.2** (ROADMAP.md): perceived-latency cut and the recording HUD are the two highest-impact items; sound cues and launch-at-login round it out.

### Environment facts

- Run: `uv run undertone` · tests: `uv run pytest` · deps: `uv sync`
- Config: `~/.config/undertone/config.toml` · log: `~/.config/undertone/undertone.log`
- Ollama: `/opt/homebrew/bin/ollama`, autostarts via LaunchAgent, models in `~/.ollama/models`
- Whisper model cache: `~/.cache/huggingface/` (~1.6 GB)
