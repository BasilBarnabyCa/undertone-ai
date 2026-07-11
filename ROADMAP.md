# Roadmap — undertone

> What Wispr Flow has that we don't yet, ordered by how much each closes the felt-quality gap.
> Prereq for everything here: v1 acceptance criteria in PLAN.md verified end-to-end.
>
> **Model tags** — which Claude to run the session on: `[opus]` = well-scoped plumbing, Opus handles it (cheaper, fast mode). `[fable]` = judgment-heavy (prompt/eval design, subtle macOS internals, security design) — first-attempt-right matters. Split tags like `[opus, fable for prompts]` mean: build on Opus, switch for the flagged part.

## The moat — what Wispr Flow structurally can't copy

Parity features (dictionary, tone matching, hands-free) close the gap; these two pillars *open* one. Both exist because undertone is local, open, and user-owned — a cloud SaaS can't follow.

1. **Privacy as a provable guarantee.** Wispr Flow sends audio to the cloud; undertone never does. That's a wedge into users they can't serve: lawyers, doctors, journalists with sources, anyone under NDA, anyone offline. Lands as **Confidential mode** + **secure-field awareness** (v0.4) — privacy as the headline, not a footnote.
2. **Programmability.** Wispr Flow is a closed app; undertone owns the code *and* the local LLM, so cleanup is just one of arbitrarily many transforms. Lands as **Programmable modes** (v0.3 centerpiece), then **local translation** (free consequence of modes) and **action hooks** (voice → automation, not just voice → text).

## v0.2 — Feels fast, feels alive

The two things you notice most in the real product: text appears almost instantly, and you can see it's listening.

- [x] ~~**Perceived-latency cut** — stream audio into Whisper in rolling chunks while the key is held.~~ **Investigated and rejected (2026-07-07).** Whisper always pads its input to a 30 s window, so inference is a constant ~0.48 s on the M4 Pro regardless of clip length (measured: 1.9 s, 2.5 s, and 5.2 s clips all ~0.48 s). Chunked streaming therefore saves no release latency, does *more* total inference, and hurts accuracy (a phrase transcribed in isolation lost sentence context: "send" → "sent"; `initial_prompt` didn't recover it). End-to-end latency is already ~1 s (0.5 s transcribe + ~0.43 s cleanup), under the v1 ≤2 s target; the HUD is what makes it *feel* instant. Real latency levers if ever needed: parallelize/shrink the cleanup pass, or adopt a streaming-native engine (see Parakeet in v1.0).
- [x] **Recording HUD** — shipped 2026-07-07: non-activating `NSPanel` pill, branded 5-bar soundwave mark, real Liquid Glass on macOS 26 with near-black fallback.
- [x] **Sound cues** — shipped 2026-07-07: Glass on start, Pop on stop, off by default, menu toggle.
- [ ] **Launch at login** `[opus]` — LaunchAgent plist, `undertone install-agent` / `uninstall-agent` commands.
- [~] **Long-hold chunking** `[opus]` — built 2026-07-11, **not yet validated on a real long recording**. Distinct from the rejected streaming item above: that was about *short* clips (Whisper's fixed-cost decode meant chunking a 2-5s clip bought nothing). This is about *long* holds, where both problems are real and confirmed in the log: transcribe time scales with length (214s of audio → 11s to transcribe), and cleanup's fixed 6s timeout reliably fails on any multi-minute transcript (silently falls back to raw text every time — cleanup effectively never ran on long dictation). `long_session.py`: once a hold crosses `chunk_seconds` (default 30s, config knob), a background `LongSession` drains the recorder every interval via the new `Recorder.take_pending()`/`close()` primitives, transcribes+cleans just that slice (small enough to land inside the cleanup timeout), and threads `initial_prompt` across chunks for context. Short dictation is completely unaffected — the threshold timer only promotes a hold past `chunk_seconds`. Trade-off carried over from the reverted experiment: a sentence split across a chunk boundary can still lose some context; `initial_prompt` mitigates but doesn't fully fix this. **Next**: test against an actual 5-15 min recording to confirm chunk-boundary quality holds up before trusting it in daily use.

## v0.3 — Programmable modes (moat centerpiece) + writes like you

The pipeline becomes user-programmable: each *mode* is a small editable prompt template the local LLM applies to the transcript. Cleanup stops being a feature and becomes just the default mode.

- [ ] **Programmable modes** `[opus, fable for the mode prompts]` — a `~/.config/undertone/modes/` folder of prompt templates; menu picker for the active mode. Ship with: Clean (today's default), Verbatim (no LLM), Email (formal), Bullets (rambling → structured list), Commit-message. Users add their own by dropping in a file — a transform Wispr Flow will never let you write. Folder/menu/pipeline plumbing is Opus work; writing prompts a 3B model reliably obeys is Fable work (see the answering-questions bug, 23c6c5f).
- [ ] **App-aware mode defaults** `[opus]` — detect the frontmost app (`NSWorkspace.frontmostApplication`) and pick a default mode per app: casual for Slack/Discord/Messages, formal for Mail, Verbatim for terminals and IDEs (never "improve" code or shell commands). Subsumes the old "tone matching" item — it's just mode routing now.
- [ ] **Local translation mode** `[fable]` — speak any language, English lands at the cursor, zero cloud. Falls out of modes nearly for free; a killer demo Wispr Flow can't do privately. Fable because it's pure prompt/eval work on the small model, and quality is the demo.
- [ ] **Personal dictionary** `[opus]` — user-maintained word list (`~/.config/undertone/dictionary.txt`): names, jargon, product terms. Injected into Whisper's `initial_prompt` *and* every mode's prompt ("prefer these spellings").
- [ ] **Self-correction handling** `[fable]` — make the Clean mode resolve spoken edits: "Tuesday — no wait, Thursday" → "Thursday". Add regression examples to a prompt test file. Judgment-heavy prompt work with subtle failure modes.
- [x] **Cleanup prompt tuning** `[fable]` — done 2026-07-07: built `evals/` (15 messy→expected cases seeded with every real failure hit in testing, plus a runner with word-level fidelity scoring). Tuned the prompt from 13/15 to a stable **15/15 exact**: concrete lexical rules beat abstractions on a 3B model, and the winning lever for the stubborn paraphrase was restating the two hardest constraints *inside every user turn* (point-of-action reminder), not in the system prompt. Remaining (open): compare alternate models (`gemma3:4b`, `qwen3:4b`) against the same eval — one command: `uv run python evals/run_cleanup_eval.py --model gemma3:4b`.

## v0.4 — Ergonomics & trust

- [ ] **Hands-free mode** `[opus]` — double-tap the hotkey to lock recording, tap again to stop (Wispr Flow's gesture; long dictations shouldn't require a held finger).
- [ ] **Chord hotkey option** `[fable]` — support e.g. Ctrl+Opt as the trigger; a two-key chord nearly eliminates accidental fires (Wispr Flow's fallback default). Fable because it bundles the CGEventTap work (true Esc capture) — low-level, system-wide, easy to get subtly wrong.
- [ ] **Dictation history** `[opus]` — menu bar submenu with the last ~10 transcripts, click to re-copy. Local only, cap length, `history_enabled` config flag for the privacy-minded.
- [ ] **Raw-vs-cleaned escape hatch** `[opus]` — after a paste, a "Undo cleanup" menu action that re-pastes the raw Whisper text (for when the LLM mangles something).
- [ ] **Confidential mode (moat)** `[opus]` — a visible "0 bytes left this device" assurance: skip even localhost Ollama, show a badge in the HUD, work with Wi-Fi off. Turns "local" from a footnote into the selling point for lawyers/doctors/journalists/NDA work.
- [ ] **Secure-input awareness (moat)** `[opus]` — detect password fields / secure input mode and refuse to capture or paste (`IsSecureEventInputEnabled`), with a notification explaining why. Privacy headline, not a footnote.
- [ ] **Action hooks (moat)** `[fable for design, opus for build]` — route the result somewhere other than paste: append to a file, POST to a localhost webhook, run an AppleScript/shell hook. Voice → automation, not just voice → text. Build after modes prove out. Fable for the security design pass (escaping, confirmation, sandboxing of user-defined hooks); Opus can implement the agreed design.
- [ ] **Better failure surfacing** `[opus]` — macOS notifications for missing permissions, Ollama down, mic unavailable; not just log lines.

## v1.0 — A real app

- [ ] **Model manager** `[opus, fable for the Parakeet evaluation]` — menu UI to pick/download Whisper models (small.en for speed vs large-v3-turbo for accuracy); evaluate **Parakeet v3 (MLX)** as the default engine — competitors ship it and it's meaningfully faster than Whisper on Apple Silicon. The engine evaluation (accuracy/latency tradeoffs, streaming-native potential) is Fable work; the picker UI is Opus.
- [ ] **Multilingual** `[opus]` — language auto-detect and per-dictation override (translation itself ships earlier as a v0.3 mode).
- [ ] **Packaged .app** `[opus]` — signed, notarized menu bar app (py2app/briefcase, or evaluate a Swift rewrite of the shell while keeping the Python pipeline). Removes the terminal-window requirement and makes permissions attach to the app itself.
- [ ] **Settings window** `[opus]` — edit hotkey, models, and toggles in a UI instead of the TOML file (keep the TOML as source of truth).

## Explicitly not chasing

- Cloud transcription of any kind — being 100% local *is* the product.
- Wispr Flow's team/enterprise features (shared dictionaries, admin, SSO).
- Mobile.
