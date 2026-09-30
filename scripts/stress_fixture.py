#!/usr/bin/env python3
"""Build a large replay by repeating COMPLETE validated GPS sentences."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from capture import private_file
from gps_fixture import parse_window


def make_payload(source, size):
    if type(size) is not int or not 1 <= size <= 16 * 1024 * 1024:
        raise ValueError("size must be 1..16777216 bytes")
    sentences, start, end = parse_window(source)
    cycle = source[start:end]
    # Exclude edge fragments BEFORE repeating, never in a received comparison.
    payload = (cycle * ((size + len(cycle) - 1) // len(cycle)))[:size]
    return payload, {"source_bytes": len(source), "source_sha256": hashlib.sha256(source).hexdigest(),
        "cycle_bytes": len(cycle), "cycle_sentences": len(sentences), "source_prefix_excluded": start,
        "source_suffix_excluded": len(source) - end, "bytes": size,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "source": "Repeated stored GPS workload, NOT new live GPS acquisition",
        "note": "Only final payload edge may be partial. Compare ALL payload bytes."}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--bytes", type=int, default=1048576)
    a = p.parse_args()
    try:
        payload, report = make_payload(a.input.read_bytes(), a.bytes)
        # Reject all collisions before touching either output.
        if a.output == a.report or any(path.exists() for path in (a.output, a.report)):
            raise FileExistsError("choose two unused output filenames")
        with private_file(a.output, True) as stream:
            stream.write(payload)
        with private_file(a.report) as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(json.dumps(report, indent=2))
    except (OSError, ValueError) as exc:
        print(f"FAIL stress fixture: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
