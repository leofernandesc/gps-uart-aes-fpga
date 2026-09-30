#!/usr/bin/env python3
"""Render the paper's numeric macros directly from the frozen fit snapshot."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from manuscript_check import SNAPSHOT, load_metrics


def render(snapshot=SNAPSHOT):
    metrics = load_metrics(snapshot)
    designs = metrics["designs"]
    values = {
        "BaselineLE": designs["baseline"]["logic_elements"],
        "BaselineReg": designs["baseline"]["registers"],
        "BaselineFmax": f'{designs["baseline"]["fmax_mhz_min"]:.2f}',
        "SecureLE": designs["secure"]["logic_elements"],
        "SecureReg": designs["secure"]["registers"],
        "SecureFmax": f'{designs["secure"]["fmax_mhz_min"]:.2f}',
    }
    return "".join(f"\\newcommand{{\\{name}}}{{{value}}}\n" for name, value in values.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        contents = render(args.snapshot)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            if args.output.read_text(encoding="utf-8") != contents:
                raise ValueError(f"existing generated macros are stale: {args.output}")
        else:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(contents)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Cannot render paper metrics: {exc}", file=sys.stderr)
        return 1
    print(f"PASS paper metric macros from {args.snapshot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
