#!/usr/bin/env python3
"""Validate the public NMEA replay and raw GPS serial captures."""
import argparse
import hashlib
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = ROOT / "reference/gps/neo-m8n-nmea-sample.txt"


def _parse_sentence(line: str, line_number: int) -> str:
    if not line or not line.startswith("$"):
        raise ValueError(f"line {line_number}: NMEA sentence must start with '$'")
    if line.count("*") != 1:
        raise ValueError(f"line {line_number}: NMEA sentence must contain one checksum separator")
    body, supplied = line[1:].rsplit("*", 1)
    if len(body) < 5 or not re.fullmatch(r"[A-Za-z0-9]{5}", body[:5]):
        raise ValueError(f"line {line_number}: invalid NMEA sentence identifier")
    if any(ord(char) < 0x20 or ord(char) > 0x7e for char in body):
        raise ValueError(f"line {line_number}: sentence contains non-printable ASCII")
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
    if len(line) + 2 > 82:
        raise ValueError(f"line {line_number}: sentence plus CRLF exceeds the 82-character NMEA limit")
    return line


def sentences(path: Path = DEFAULT_FIXTURE) -> list[str]:
    raw = path.read_bytes()
    # Git may materialize the checked-in LF fixture as CRLF on Windows.  Treat
    # that checkout conversion as equivalent, while still rejecting bare CR.
    raw = raw.replace(b"\r\n", b"\n")
    if b"\r" in raw:
        raise ValueError(f"{path}: source fixture must use LF-delimited sentences")
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


def parse_payload(payload: bytes) -> list[str]:
    """Validate and return sentences from a complete raw GPS UART capture.

    A capture is intentionally stricter than the checked-in LF-delimited
    fixture: the serial stream must contain complete ASCII sentences delimited
    by CRLF.  This catches a truncated capture, line-ending conversion, bad
    checksum, or framing that would otherwise make a later byte comparison
    misleading.
    """
    if not payload:
        raise ValueError("capture is empty")
    if not payload.endswith(b"\r\n"):
        raise ValueError("capture must end at a complete CRLF-delimited sentence")
    remainder = payload.replace(b"\r\n", b"")
    if b"\r" in remainder or b"\n" in remainder:
        raise ValueError("capture contains a bare CR or LF; expected CRLF delimiters")
    raw_sentences = payload[:-2].split(b"\r\n")
    if any(not raw_sentence for raw_sentence in raw_sentences):
        raise ValueError("capture contains an empty NMEA sentence")
    parsed = []
    for line_number, raw_sentence in enumerate(raw_sentences, 1):
        try:
            line = raw_sentence.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"line {line_number}: sentence is not ASCII") from exc
        parsed.append(_parse_sentence(line, line_number))
    return parsed


def _display_path(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def capture_metadata(path: Path) -> dict[str, object]:
    """Return reproducible metadata for a raw GPS capture file."""
    path = path.resolve()
    payload = path.read_bytes()
    parsed = parse_payload(payload)
    sentence_types = Counter(sentence[1:6] for sentence in parsed)
    return {
        "status": "PASS",
        "path": _display_path(path),
        "sentences": len(parsed),
        "sentence_types": dict(sorted(sentence_types.items())),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "line_ending": "CRLF",
        "source": "raw serial capture; physical origin must be documented separately",
    }


def metadata(path: Path = DEFAULT_FIXTURE) -> dict[str, object]:
    path = path.resolve()
    parsed = sentences(path)
    payload = b"".join(sentence.encode("ascii") + b"\r\n" for sentence in parsed)
    return {
        "status": "PASS",
        "path": _display_path(path),
        "sentences": len(parsed),
        "sentence_types": dict(sorted(Counter(sentence[1:6] for sentence in parsed).items())),
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
