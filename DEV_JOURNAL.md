# Dev Journal — undertone

> One entry per session, newest first. The top entry's "Next steps" is the handoff.

## 2026-07-11 (later) — long-hold chunking built (not yet validated on real audio)

Follow-on from the recording bug below: Basil noticed long conversations also
take a long time to come back after release, and asked whether chunks could
be sent off every ~30s while still recording, in parallel with capturing the
next slice. Built on Opus (concurrency/systems plumbing — the right call per
the moat-tags framework: subtle races here would mean silently dropped audio,
same failure category as the bug this follows).

**This is not a repeat of the reverted streaming experiment.** That was about
short clips (Whisper pads every call to a fixed ~30s window, so chunking a
2-5s clip bought zero latency and cost accuracy). This is about long holds,
where the log already proved two real, scaling costs: transcribe time grows
with clip length (214s of audio took 11s to transcribe), and — this was the
sharper find — **cleanup's fixed 6s timeout has been silently failing on
every multi-minute transcript in the log**, meaning LLM cleanup has
effectively never run on real long-form dictation.

### Done

1. **`recorder.py`**: added a lock and `take_pending()` (non-destructive
   drain — grabs and clears buffered frames while the stream keeps running)
   and `close()` (stream teardown without the `clip_ok` gate). `stop()` is
   now `close()` + gating — the short-hold fast path is behaviorally
   unchanged.
2. **`transcriber.py`**: `transcribe()` takes an optional `initial_prompt`,
   threaded across chunks for boundary context.
3. **`long_session.py`** (new): `LongSession` — once a hold crosses
   `chunk_seconds`, drains the recorder every interval, transcribes+cleans
   just that slice, appends it. `finish()` processes the trailing partial
   slice after the recorder closes; `stop()` aborts without one (cancel path).
   One bad slice logs and gets dropped rather than costing the whole
   recording.
4. **`app.py`**: a `threading.Timer` armed on key-down promotes to a
   `LongSession` only past `cfg.chunk_seconds` (default 30s) — short
   dictation never touches this code path at all. Closed a narrow race where
   the promotion timer could fire in the same instant as key-up (already
   running when `.cancel()` is called doesn't stop it) by defensively
   stopping any late-created session in the short-hold branch too.
5. **`config.py`**: new `chunk_seconds` knob (default 30.0).
6. Tests: `test_recorder.py` (take_pending/close/stop primitives),
   `test_transcriber.py` (initial_prompt forwarding), `test_long_session.py`
   (chunking, context-threading, cleanup toggle, exception isolation,
   finish/stop semantics) — 20 new tests, 34/34 passing. `app.py`'s wiring
   itself isn't unit-tested (same reason as always: needs rumps/AppKit), so
   it was traced through by hand instead.

### Known gap — not yet validated

Everything above is reasoned/tested at the unit level; **none of it has run
against a real long recording yet.** The open question from the reverted
experiment — does splitting a monologue into independent Whisper calls lose
meaningful context at the seams — is worse here (more seams over 15 minutes)
even with `initial_prompt` threading. Test on a real long hold before relying
on it for anything that matters.

### Next steps, in order

1. **Validate on a real 5-15 min recording** — check chunk-boundary
   transcript quality, and confirm the cleanup timeout now actually succeeds
   per-chunk instead of always failing open.
2. Commit this alongside the still-pending recording-bug fix, eval harness,
   and logo/icon batches — all uncommitted going into this session.
3. Everything below carries over unchanged.

## 2026-07-11 — bug: 15-min recording captured nothing, icon stuck

Basil held the hotkey through a ~15 min conversation; on release, nothing was
pasted and the menu bar mark never looked busy. Root cause found in the log
(`~/.config/undertone/undertone.log` had a `PortAudioError: Error opening
InputStream [PaErrorCode -9986]` traceback):

- `Recorder.start()` called `sd.InputStream(...)` with no error handling.
- `_on_key_down` (app.py) called `hud.show()` → `sounds.start()` →
  `recorder.start()` — also uncaught. When the stream failed to open,
  `recorder.recording` stayed `False`.
- `_on_key_up` no-ops on `if not self.recorder.recording`, so it never called
  `hud.hide()` — the whole 15 min was spoken into a stream that failed at the
  very first instant, with zero visible feedback.

**Fix**: `_on_key_down` now catches the failure, hides the HUD, stops the
sound cue, and shows the ⚠️ warning glyph instead of silently doing nothing.
`Recorder.start()` also now only assigns `self._stream` after `.start()`
succeeds, so a partial failure can't leave `recording` reporting `True` for a
stream that isn't actually live. No test added — app.py isn't unit-tested
(needs rumps/AppKit); reasoned through the fix against the log evidence
instead.

**Not fixed / still true**: audio is never persisted to disk — if the same
class of failure recurs mid-recording (not just at open), or paste/cleanup
fails after a long dictation, the words are gone. Worth a disk safety-net
(write raw frames to a scratch wav) if this recurs.

### Next steps, in order

1. **Commit this fix** along with the still-pending eval harness batch and
   logo/icon-template batch (all uncommitted going into this session).
2. Watch for a recurrence — if `PortAudioError` shows up again, consider a
   raw-audio-to-disk safety net so a long recording is never silently lost.
3. Everything below carries over unchanged.

## 2026-07-07 (evening) — cleanup eval harness built, prompt tuned to 15/15

First `[fable]`-tagged roadmap item done (see ROADMAP.md model tags, added this session along with the moat pillars).

### Done

1. **`evals/cases.jsonl`** — 15 messy→expected cases seeded with every real failure hit so far: answering a dictated question, dropping "Testing"/"I think", paraphrasing "is it possible"→"can you", plus fillers, false starts, homophones, dictated punctuation, negation, numbers, jargon casing.
2. **`evals/run_cleanup_eval.py`** — runner with word-level fidelity scoring (EXACT / PASS-normalized / FAIL); `--model` flag ready for alternate-model comparison; multiple accepted variants per case.
3. **Prompt tuned 13/15 → stable 15/15 exact** (verified across repeated runs; failures were deterministic, not noise). What worked, in order of impact:
   - **Point-of-action reminder** — restating "do not answer it, do not reword it" inside *every user turn* fixed the paraphrase that survived both the system prompt and a literal few-shot example. Small models weigh the end of context most.
   - **Concrete lexical rules** — "never insert 'that', keep every and/but/or instead of semicolons" worked where abstract "preserve wording" didn't.
   - **Targeted few-shot examples** (now 4) — each added to kill a specific observed failure, incl. the leading-gerund "title formatting" instinct.
   - Temperature 0.1 → 0.0.

### Next steps, in order

1. **Commit** the eval harness + tuned prompt (`evals/`, `cleanup.py`, `test_cleanup.py`, ROADMAP, this entry).
2. **Optional model comparison** (Basil said hold off earlier; one command when ready): `ollama pull gemma3:4b && uv run python evals/run_cleanup_eval.py --model gemma3:4b`.
3. **Launch at login** `[opus]` — last v0.2 item; switch back to Opus for it.
4. **v0.3 programmable modes** — plumbing `[opus]`, mode prompts `[fable]`; the eval harness is the regression net for every mode.
5. Voice-based v1 checks + folder rename still open (see previous entries).

## 2026-07-07 (afternoon) — streaming latency cut: built, measured, reverted

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
