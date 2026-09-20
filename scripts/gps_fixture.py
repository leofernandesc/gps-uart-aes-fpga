#!/usr/bin/env python3
"""Validate and load the public NMEA replay used by RTL/PC tests."""
import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = ROOT / "reference/gps/neo-m8n-nmea-sample.txt"


def _parse_sentence(line: str, line_number: int) -> str:
    if not line or not line.startswith("$"):
        raise ValueError(f"line {line_number}: NMEA sentence must start with '$'")
    if line.count("*") != 1:
        raise ValueError(f"line {line_number}: NMEA sentence must contain one checksum separator")
    body, supplied = line[1:].rsplit("*", 1)
    if len(supplied) != 2:
        raise ValueError(f"line {line_number}: checksum must contain two hexadecimal digits")
    try:
        expected = int(supplied, 16)
    except ValueError as exc:
        raise ValueError(f"line {line_number}: checksum is not hexadecimal") from exc
    checksum = 0
    try:
        encoded = body.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"line {line_number}: sentence is not ASCII") from exc
    for byte in encoded:
        checksum ^= byte
    if checksum != expected:
        raise ValueError(f"line {line_number}: checksum {supplied.upper()} != {checksum:02X}")
    if len(line) > 82:
        raise ValueError(f"line {line_number}: sentence exceeds the 82-character NMEA limit")
    return line


def sentences(path: Path = DEFAULT_FIXTURE) -> list[str]:
    raw = path.read_bytes()
    if b"\r" in raw:
        raise ValueError(f"{path}: source fixture must use one LF-delimited sentence per line")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: source fixture must be ASCII") from exc
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise ValueError(f"{path}: fixture is empty")
    if any(not line for line in lines):
        raise ValueError(f"{path}: empty NMEA sentence")
    return [_parse_sentence(line, index) for index, line in enumerate(lines, 1)]


def load_replay(path: Path = DEFAULT_FIXTURE) -> bytes:
    """Return the fixture as the byte stream emitted by a GPS UART (CRLF)."""
    return b"".join(sentence.encode("ascii") + b"\r\n" for sentence in sentences(path))


def metadata(path: Path = DEFAULT_FIXTURE) -> dict[str, object]:
    path = path.resolve()
    parsed = sentences(path)
    payload = b"".join(sentence.encode("ascii") + b"\r\n" for sentence in parsed)
    try:
        display_path = str(path.relative_to(ROOT))
    except ValueError:
        display_path = str(path)
    return {
        "status": "PASS",
        "path": display_path,
        "sentences": len(parsed),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "line_ending": "CRLF",
        "source": "public synthetic replay; not a physical GPS capture",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    result = metadata(args.path.resolve())
    print(
        "PASS GPS NMEA replay: "
        f"{result['sentences']} sentences, {result['bytes']} bytes, "
        f"CRLF, SHA-256 {result['sha256']}"
    )


if __name__ == "__main__":
    main()
