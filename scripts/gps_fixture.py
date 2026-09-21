#!/usr/bin/env python3
"""Validate the public NMEA replay and raw GPS serial captures."""
import argparse
import hashlib
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = ROOT / "reference/gps/neo-m8n-nmea-sample.txt"


def _parse_sentence(line: str, line_number: int, max_sentence_bytes: int = 82) -> str:
    if type(max_sentence_bytes) is not int or not 9 <= max_sentence_bytes <= 4096:
        raise ValueError("max_sentence_bytes must be an integer in [9, 4096]")
    if any(not 0x20 <= ord(char) <= 0x7e for char in line):
        raise ValueError(f"line {line_number}: sentence must contain printable ASCII only")
    if not line or not line.startswith("$"):
        raise ValueError(f"line {line_number}: NMEA sentence must start with '$'")
    if line.count("*") != 1:
        raise ValueError(f"line {line_number}: NMEA sentence must contain one checksum separator")
    body, supplied = line[1:].rsplit("*", 1)
    if not re.fullmatch(r"[0-9A-Fa-f]{2}", supplied):
        raise ValueError(f"line {line_number}: checksum must contain two hexadecimal digits")
    # Standard talker/type or proprietary P + three-character manufacturer.
    if not re.match(r"(?:[A-Z]{2}[A-Z0-9]{3}|P[A-Z0-9]{3}),", body):
        raise ValueError(f"line {line_number}: invalid NMEA sentence identifier")
    expected = int(supplied, 16)
    checksum = 0
    try:
        encoded = body.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"line {line_number}: sentence is not ASCII") from exc
    for byte in encoded:
        checksum ^= byte
    if checksum != expected:
        raise ValueError(f"line {line_number}: checksum {supplied.upper()} != {checksum:02X}")
    if len(line) + 2 > max_sentence_bytes:
        raise ValueError(f"line {line_number}: sentence exceeds {max_sentence_bytes} bytes including CRLF")
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


def parse_payload(payload: bytes, max_sentence_bytes: int = 82) -> list[str]:
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
        parsed.append(_parse_sentence(line, line_number, max_sentence_bytes))
    return parsed


def parse_window(payload: bytes, max_sentence_bytes: int = 82):
    """Validate complete interior sentences; report, never delete, edge fragments.

    This is a raw acquisition window, NOT CTR resynchronization. Offsets always
    refer to the original byte stream, whose complete contents must be compared.
    """
    if not payload:
        raise ValueError("capture is empty")
    if any(byte not in (10, 13) and not 0x20 <= byte <= 0x7e for byte in payload):
        raise ValueError("capture must contain printable ASCII and CRLF only")
    first_end = payload.find(b"\r\n")
    start = 0 if payload.startswith(b"$") else first_end + 2
    end = payload.rfind(b"\r\n") + 2
    if first_end < 0 or end <= start:
        raise ValueError("capture window has no complete NMEA sentence")
    parsed = parse_payload(payload[start:end], max_sentence_bytes)
    return parsed, start, end


def _display_path(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def capture_metadata(path: Path, allow_partial_edges: bool = False, max_sentence_bytes: int = 82) -> dict[str, object]:
    """Return reproducible metadata for a raw GPS capture file."""
    path = path.resolve()
    payload = path.read_bytes()
    if allow_partial_edges:
        parsed, start, end = parse_window(payload, max_sentence_bytes)
    else:
        parsed, start, end = parse_payload(payload, max_sentence_bytes), 0, len(payload)
    sentence_types = Counter(sentence[1:].split(",", 1)[0] for sentence in parsed)
    return {
        "status": "PASS",
        "path": _display_path(path),
        "sentences": len(parsed),
        "sentence_types": dict(sorted(sentence_types.items())),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "line_ending": "CRLF",
        "validation_mode": "window" if allow_partial_edges else "complete",
        "max_sentence_bytes_including_crlf": max_sentence_bytes,
        "complete_sentence_span": {"start_offset": start, "end_offset_exclusive": end},
        "boundary_fragments": {"prefix_bytes": start, "suffix_bytes": len(payload) - end},
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
