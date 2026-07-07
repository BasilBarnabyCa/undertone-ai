# Roadmap — undertone

> What Wispr Flow has that we don't yet, ordered by how much each closes the felt-quality gap.
> Prereq for everything here: v1 acceptance criteria in PLAN.md verified end-to-end.

## v0.2 — Feels fast, feels alive

The two things you notice most in the real product: text appears almost instantly, and you can see it's listening.

- [ ] **Perceived-latency cut** — start streaming audio into Whisper in rolling chunks *while* the key is held, so release→paste drops from ~1–2 s to near-instant. Fallback if chunking hurts accuracy: transcribe-on-release but begin model inference during the final 0.5 s of held audio.
- [ ] **Recording HUD** — small floating pill (waveform or pulsing dot) while the key is held, so you're never guessing whether it heard you. `NSPanel` non-activating overlay; menu bar icon alone is too easy to miss.
- [ ] **Sound cues** — subtle start/stop ticks (system sounds, off by default in config).
- [ ] **Launch at login** — LaunchAgent plist, `undertone install-agent` / `uninstall-agent` commands.

## v0.3 — Writes like you, everywhere

Wispr Flow's retention features: output quality beyond generic cleanup.

- [ ] **Personal dictionary** — user-maintained word list (`~/.config/undertone/dictionary.txt`): names, jargon, product terms. Injected into Whisper's `initial_prompt` *and* the cleanup system prompt ("prefer these spellings").
- [ ] **App-aware tone matching** — detect the frontmost app (`NSWorkspace.frontmostApplication`) and swap cleanup prompts: casual for Slack/Discord/Messages, formal for Mail, verbatim-with-light-punctuation for terminals and IDEs (never "improve" code or shell commands).
- [ ] **Self-correction handling** — make the cleanup prompt resolve spoken edits: "Tuesday — no wait, Thursday" → "Thursday". Add regression examples to a prompt test file.
- [ ] **Cleanup prompt tuning** — current prompt is slightly too aggressive (drops "I think"). Build a small eval set of messy→expected pairs; test prompt changes and alternate models (`qwen3:4b`) against it.

## v0.4 — Ergonomics & trust

- [ ] **Hands-free mode** — double-tap the hotkey to lock recording, tap again to stop (Wispr Flow's gesture; long dictations shouldn't require a held finger).
- [ ] **Chord hotkey option** — support e.g. Ctrl+Opt as the trigger; a two-key chord nearly eliminates accidental fires (Wispr Flow's fallback default).
- [ ] **Dictation history** — menu bar submenu with the last ~10 transcripts, click to re-copy. Local only, cap length, `history_enabled` config flag for the privacy-minded.
- [ ] **Raw-vs-cleaned escape hatch** — after a paste, a "Undo cleanup" menu action that re-pastes the raw Whisper text (for when the LLM mangles something).
- [ ] **Secure-input awareness** — detect password fields / secure input mode and refuse to paste (`IsSecureEventInputEnabled`), with a notification explaining why.
- [ ] **Better failure surfacing** — macOS notifications for missing permissions, Ollama down, mic unavailable; not just log lines.

## v1.0 — A real app

- [ ] **Model manager** — menu UI to pick/download Whisper models (small.en for speed vs large-v3-turbo for accuracy); evaluate **Parakeet v3 (MLX)** as the default engine — competitors ship it and it's meaningfully faster than Whisper on Apple Silicon.
- [ ] **Multilingual** — language auto-detect, per-dictation override, optional speak-in-X-output-in-English translation via the cleanup model.
- [ ] **Packaged .app** — signed, notarized menu bar app (py2app/briefcase, or evaluate a Swift rewrite of the shell while keeping the Python pipeline). Removes the terminal-window requirement and makes permissions attach to the app itself.
- [ ] **Settings window** — edit hotkey, models, and toggles in a UI instead of the TOML file (keep the TOML as source of truth).

## Explicitly not chasing

- Cloud transcription of any kind — being 100% local *is* the product.
- Wispr Flow's team/enterprise features (shared dictionaries, admin, SSO).
- Mobile.
