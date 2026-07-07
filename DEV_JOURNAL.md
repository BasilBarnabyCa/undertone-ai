# Dev Journal — undertone

> One entry per session, newest first. The top entry's "Next steps" is the handoff.

## 2026-07-07 (latest) — streaming latency cut: built, measured, reverted

Attempted the roadmap's headline v0.2 item (stream audio into Whisper in rolling chunks so release→paste feels instant). Built it fully — `streaming.py` with silence-aligned phrase finalization + `initial_prompt` context threading, recorder `snapshot()`, config flag, 8 tests. Then measured it end-to-end and **reverted the whole thing.**

**Why reverted (the load-bearing finding):** Whisper pads every input to a 30 s window, so inference time is ~constant (~0.48 s on the M4 Pro) whether the clip is 1.9 s or 5.2 s. Chunked streaming saves ~0 release latency, does more total inference, and *hurts* accuracy — a phrase transcribed without the rest of the sentence lost context ("send John" → "sent John"), and `initial_prompt` didn't fix it. Net: strictly worse. Full analysis in ROADMAP.md (item now marked done/rejected).

**Takeaway:** end-to-end latency is already ~1 s (0.5 s transcribe + ~0.43 s cleanup), under the ≤2 s target; the HUD makes it *feel* instant. Don't re-attempt chunked Whisper. Real latency levers if ever needed: parallelize/shrink the cleanup pass, or a streaming-native engine (Parakeet, v1.0).

### Next steps, in order

1. **Continue v0.2**: sound cues (start/stop ticks, off by default) or launch-at-login (LaunchAgent + install/uninstall commands) — both small, self-contained, no voice needed.
2. **Finish v1 acceptance checks** (voice-dependent): browser text field, cleanup on/off comparison, ≤2 s latency feel.
3. **Basil to eyeball** the HUD glass pill and menu bar mark; tweak tint/brightness/size as desired.
4. **Rename the project folder** (outside a session): `mv ~/dev/ai/whisper-flow-clone ~/dev/ai/undertone`.

## 2026-07-07 (later) — v0.2 starts: recording HUD, Liquid Glass, menu bar mark

Cleanup answering-bug fixed earlier this session; then moved into v0.2 visual polish and brand.

### Done

1. **Recording HUD** (`hud.py`): a floating, non-activating `NSPanel` pill shown while the hotkey is held so you can see it's listening. Undertone's mark — a bell-curved cluster of 5 pill bars (mint `#8CFFEC` → electric cyan `#22E8FF` → deep blue `#00B4FF`, symmetric) — animates as a soundwave via staggered vertical scaling. Faint close-in glow per bar. Thread-safe: `show()`/`hide()` marshal to the main thread (`AppHelper.callAfter`).
2. **Liquid Glass** (`hud.py`): the pill is a real `NSGlassEffectView` (macOS 26 Tahoe), dark-tinted to keep the near-black brand while gaining real refraction/specular edges. Falls back to a near-black layer pill on < macOS 26.
3. **Menu bar mark** (`icons.py`): the same soundwave rendered as a crisp 40px (retina) colored PNG, two variants — `active` (running) and `muted` (warming up / busy) — written to `~/.config/undertone/`. `app.py` swaps the mark by state and shows ⚠️ text only on warm-up failure. Replaced the old emoji state machine (🎤/🔴/⏳/⌛).

### Known issues / observations

- **Real logo never received** — the attachment kept arriving as the generic macOS "PNG file" placeholder, so the mark is drawn from Basil's written brand spec, not his file. Swap in the real asset when available (tune bar proportions).
- **Colored (non-template) menu bar icon** — stays cyan-blue in light and dark menu bars rather than adapting to monochrome. Intentional for a brand mark; revisit if it reads busy on a light bar.
- HUD glass only shows its refraction against live desktop content; preview via `scratchpad/hud_preview.py`.

### Next steps, in order

1. **Basil to eyeball** the HUD glass pill and menu bar mark; tweak tint/brightness/size as desired.
2. **Finish v1 acceptance checks** (voice-dependent): browser text field, cleanup on/off comparison, ≤2s latency feel.
3. **Continue v0.2** (ROADMAP.md): perceived-latency cut (stream audio into Whisper while held), sound cues, launch-at-login LaunchAgent.
4. **Rename the project folder** (outside a session): `mv ~/dev/ai/whisper-flow-clone ~/dev/ai/undertone`.

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
