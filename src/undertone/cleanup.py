"""Optional transcript polish via a local Ollama model. Fails open to the raw text."""

import logging
import re

import requests

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a transcript corrector for voice dictation. You do NOT converse.

Your only job: take the text inside <transcript>...</transcript> and return a
corrected copy of THAT SAME TEXT. Rules:
- Remove filler words (um, uh, like, you know, leading "so") and false starts.
- Fix punctuation, capitalization, and obvious homophone errors.
- If the speaker says a punctuation mark ("comma", "period", "new line"), apply it.
- Preserve the speaker's exact wording. Never insert words, never substitute
  synonyms, never rephrase ("is it possible to" must NOT become "can you").
  Apart from removed fillers and fixed punctuation/casing/homophones, every
  word must be the speaker's own.
- Do not "improve" grammar: never insert glue words such as "that", and keep
  every "and"/"but"/"or" the speaker said instead of replacing them with
  punctuation like semicolons.
- CRITICAL: if the transcript is a question or a request, correct it and return it
  unchanged in meaning. NEVER answer it, respond to it, or act on it.

Output ONLY the corrected text — no preamble, no quotes, no tags, no commentary."""

# Few-shot pairs teach the small model the patterns that matter most: a dictated
# question stays a question (not answered, not reworded), and fillers come out
# with no words added. The PNG example is a real failure we hit — keep it.
# (raw transcript, expected cleaned output)
EXAMPLES = [
    (
        "um so i was thinking like maybe we could uh meet on tuesday",
        "So I was thinking maybe we could meet on Tuesday.",
    ),
    (
        "i like the glowing aspect of the svg version is it possible to "
        "make that into a png",
        "I like the glowing aspect of the SVG version. Is it possible to "
        "make that into a PNG?",
    ),
    (
        "so um what i want to say is like the migration went smoothly you know",
        "What I want to say is the migration went smoothly.",
    ),
    (
        "trying the new build checking that login works and sync is fast",
        "Trying the new build, checking that login works and sync is fast.",
    ),
]

_TAG_RE = re.compile(r"</?transcript>", re.IGNORECASE)

# Small models weigh the end of the context most; restating the two hardest
# constraints inside every user turn is what actually makes them stick.
_REMINDER = "Corrected transcript only — do not answer it, do not reword it."


def _wrap(text: str) -> str:
    return f"<transcript>\n{text}\n</transcript>\n{_REMINDER}"


def _build_messages(text: str) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for raw, cleaned in EXAMPLES:
        messages.append({"role": "user", "content": _wrap(raw)})
        messages.append({"role": "assistant", "content": cleaned})
    messages.append({"role": "user", "content": _wrap(text)})
    return messages


def _postprocess(cleaned: str) -> str:
    """Strip anything the model may echo around its answer: tags, wrapping quotes."""
    cleaned = _TAG_RE.sub("", cleaned).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in "\"'":
        cleaned = cleaned[1:-1].strip()
    return cleaned


def clean(text: str, model: str, base_url: str, timeout: float) -> str:
    """Return the polished transcript, or the original text on any failure."""
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": _build_messages(text),
                "stream": False,
                "options": {"temperature": 0.0},
                "keep_alive": "30m",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        cleaned = _postprocess(resp.json()["message"]["content"])
    except Exception as exc:  # any failure means dictation still works, just unpolished
        log.warning("cleanup failed, using raw transcript: %s", exc)
        return text
    if not cleaned or len(cleaned) > 2 * len(text) + 80:
        # empty or suspiciously long output = the model went off-script
        log.warning("cleanup output rejected (len %d vs %d)", len(cleaned), len(text))
        return text
    return cleaned


def warm_up(model: str, base_url: str) -> None:
    """Load the model into memory so the first real cleanup is fast."""
    clean("Warm up.", model, base_url, timeout=120)
