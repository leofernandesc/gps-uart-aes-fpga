#!/usr/bin/env python3
"""Validate a complete raw GPS/NMEA capture before an experiment."""
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
        # Windows does not apply POSIX creation modes through os.open; keep
        # the explicit permission intent for platforms that expose it.
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
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
    args = parser.parse_args()
    try:
        result = capture_metadata(args.input)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
