"""Optional transcript polish via a local Ollama model. Fails open to the raw text."""

import logging

import requests

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You clean up voice dictation transcripts. Rules:
- Remove filler words (um, uh, like, you know) and false starts.
- Fix punctuation, capitalization, and obvious homophone errors.
- Keep the speaker's words and meaning exactly; never add, summarize, or answer.
- If the speaker dictates punctuation ("comma", "new line"), apply it.
Output ONLY the cleaned text, nothing else."""


def clean(text: str, model: str, base_url: str, timeout: float) -> str:
    """Return the polished transcript, or the original text on any failure."""
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "options": {"temperature": 0.1},
                "keep_alive": "30m",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        cleaned = resp.json()["message"]["content"].strip()
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
