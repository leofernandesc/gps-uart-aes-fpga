#!/usr/bin/env python3
"""Check that manuscript drafts retain current results and evidence limits."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent

REQUIREMENTS = {
    "English": (
        ROOT / "docs/manuscrito-btsym-draft.md",
        (
            "50 MHz",
            "9600 baud",
            "309 bytes",
            "342",
            "6,984",
            "82.19 MHz",
            "synthetic replay",
            "physical",
        ),
    ),
    "Portuguese": (
        ROOT / "docs/manuscrito-btsym-rascunho-pt.md",
        (
            "50 MHz",
            "9600 baud",
            "309 bytes",
            "342",
            "6.984",
            "82,19 MHz",
            "replay público/sintético",
            "físic",
        ),
    ),
}


def check_draft(label: str, path: Path, markers: tuple[str, ...]) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{label}: cannot read {path}: {exc}"]
    missing = [marker for marker in markers if marker not in text]
    return [f"{label}: missing required disclosure/result: {marker!r}" for marker in missing]


def main() -> int:
    failures = []
    for label, (path, markers) in REQUIREMENTS.items():
        draft_failures = check_draft(label, path, markers)
        failures.extend(draft_failures)
        if not draft_failures:
            print(f"PASS manuscript check: {label} draft")
    if failures:
        for failure in failures:
            print(f"FAIL manuscript check: {failure}", file=sys.stderr)
        return 1
    print("PASS manuscript check: current metrics and physical-validation limits are disclosed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
