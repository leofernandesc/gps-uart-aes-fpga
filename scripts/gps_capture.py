#!/usr/bin/env python3
"""Validate complete NMEA sentences without modifying the raw GPS capture."""
import argparse
import json
import os
from pathlib import Path
import sys

from gps_fixture import capture_metadata


def private_report(path: Path, result: dict[str, object]) -> None:
    """Write a report once, with permissions suitable for private experiments."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="raw binary GPS capture")
    parser.add_argument("--report", type=Path, help="optional new JSON report")
    parser.add_argument("--allow-partial-edges", action="store_true", help="validate complete interior sentences and report boundary offsets")
    parser.add_argument("--max-sentence-bytes", type=int, default=82, help="declared NMEA profile limit INCLUDING CRLF (default 82)")
    args = parser.parse_args()
    try:
        result = capture_metadata(args.input, args.allow_partial_edges, args.max_sentence_bytes)
        if args.report:
            private_report(args.report, result)
    except (OSError, ValueError) as exc:
        print(f"FAIL GPS capture: {exc}", file=sys.stderr)
        return 1

    types = ", ".join(f"{name}={count}" for name, count in result["sentence_types"].items())
    print(
        "PASS GPS capture: "
        f"{result['sentences']} sentences, {result['bytes']} bytes, "
        f"CRLF, types [{types}], SHA-256 {result['sha256']}"
    )
    if args.report:
        print(f"Report: {args.report}")
    if args.allow_partial_edges:
        print(f"Boundary fragments (raw bytes preserved): {result['boundary_fragments']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
