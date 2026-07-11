"""Run the cleanup-prompt eval set against a live Ollama model.

Usage (from the repo root):
    uv run python evals/run_cleanup_eval.py                # default model
    uv run python evals/run_cleanup_eval.py --model gemma3:4b

Each case in cases.jsonl is a messy transcript plus one or more acceptable
cleaned outputs. A case passes if the model output matches any variant:

- EXACT: string-identical to a variant.
- PASS:  same words as a variant, ignoring case and punctuation (an LLM
         choosing a comma over a period is not a regression).
- FAIL:  the words themselves differ — dropped, added, or changed content.

The word-level comparison is deliberately strict: this harness exists to catch
meaning changes (answered questions, dropped hedges, paraphrases), and all of
those show up as changed words.

Known-unsupported (deliberately NOT in the case set): stacked ambiguity like
"i like the grace period they gave us period" — a 3B model can't resolve the
same token as word and punctuation in one sentence (it produced "they gave us
a period"). Escape hatch: cleanup toggle off / Verbatim mode.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from undertone import config
from undertone.cleanup import clean

CASES_PATH = Path(__file__).with_name("cases.jsonl")


def words(text: str) -> list[str]:
    """Lowercased word tokens with punctuation stripped (apostrophes kept)."""
    return re.findall(r"[a-z0-9']+", text.lower())


def grade(output: str, expected: list[str]) -> str:
    if any(output == e for e in expected):
        return "EXACT"
    if any(words(output) == words(e) for e in expected):
        return "PASS"
    return "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg = config.load()
    parser.add_argument("--model", default=cfg.ollama_model)
    parser.add_argument("--url", default=cfg.ollama_url)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--only", help="run a single case id")
    args = parser.parse_args()

    cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines() if line.strip()]
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]

    results = {"EXACT": 0, "PASS": 0, "FAIL": 0}
    t0 = time.monotonic()
    print(f"model: {args.model}\n")
    for case in cases:
        out = clean(case["input"], args.model, args.url, args.timeout)
        verdict = grade(out, case["expected"])
        results[verdict] += 1
        marker = {"EXACT": "✓", "PASS": "✓", "FAIL": "✗"}[verdict]
        print(f"{marker} {verdict:5} {case['id']}")
        if verdict == "FAIL":
            print(f"    why:      {case['why']}")
            print(f"    input:    {case['input']!r}")
            print(f"    output:   {out!r}")
            print(f"    expected: {case['expected'][0]!r}")

    total = sum(results.values())
    ok = results["EXACT"] + results["PASS"]
    print(
        f"\n{ok}/{total} passed ({results['EXACT']} exact, {results['PASS']} normalized) "
        f"— {results['FAIL']} failed — {time.monotonic() - t0:.0f}s"
    )
    return 0 if results["FAIL"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
