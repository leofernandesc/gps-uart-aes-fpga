#!/usr/bin/env python3
"""Verify structured ESP32 UART-bench logs against baseline or AES-CTR.

The verifier is deliberately fail-closed: a valid run starts at sequence 1,
contains consecutive RESULT records, has no host/UART transport errors and
uses the same five-byte stimulus in every trial.  For secure runs, ciphertext
is concatenated and independently recovered with the recorded AES-CTR context.

The public context is only for first bench bring-up.  Article acquisitions
must pass their private context JSON with --context.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from context import validate_context
from ctr_vectors import crypt


DEFAULT_VECTOR = bytes.fromhex("55a500ff3c")
PUBLIC_KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
PUBLIC_NONCE = bytes.fromhex("101112131415161718191a1b")
PUBLIC_COUNTER = 1

REQUIRED_FIELDS = {
    "seq", "mode", "tx", "rx", "rx_len", "same", "timeout", "extra",
    "frame_err", "parity_err", "fifo_ovf", "buffer_full", "break",
    "write_err", "tx_timeout", "host_window_us",
}
INTEGER_FIELDS = REQUIRED_FIELDS - {"mode", "tx", "rx"}
ERROR_FIELDS = (
    "timeout", "extra", "frame_err", "parity_err", "fifo_ovf",
    "buffer_full", "break", "write_err", "tx_timeout",
)
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SESSION_MARKER = "ESP-IDF UART host ready"


def _hex_bytes(value, label):
    if value == "-":
        return b""
    if len(value) % 2:
        raise ValueError(f"{label} has an odd number of hexadecimal digits")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{label} is not hexadecimal") from exc


def parse_results(text):
    """Return parsed RESULT records from an ESP-IDF monitor transcript."""
    records = []
    lines = text.splitlines()
    session_starts = [
        index for index, line in enumerate(lines)
        if SESSION_MARKER in ANSI_ESCAPE.sub("", line)
    ]
    start = session_starts[-1] if session_starts else 0
    for line_number, raw_line in enumerate(lines[start:], start + 1):
        line = ANSI_ESCAPE.sub("", raw_line)
        marker = re.search(r"(?:^|\s)RESULT\s+", line)
        if marker is None:
            continue
        fields = {}
        for token in line[marker.end():].split():
            if "=" not in token:
                raise ValueError(
                    f"line {line_number}: malformed RESULT token {token!r}")
            name, value = token.split("=", 1)
            if name in fields:
                raise ValueError(
                    f"line {line_number}: duplicate RESULT field {name}")
            fields[name] = value
        missing = sorted(REQUIRED_FIELDS - fields.keys())
        if missing:
            raise ValueError(
                f"line {line_number}: missing RESULT fields: {', '.join(missing)}")
        record = {"line": line_number, "mode": fields["mode"]}
        record["tx"] = _hex_bytes(fields["tx"], f"line {line_number} tx")
        record["rx"] = _hex_bytes(fields["rx"], f"line {line_number} rx")
        for name in INTEGER_FIELDS:
            try:
                record[name] = int(fields[name], 10)
            except ValueError as exc:
                raise ValueError(
                    f"line {line_number}: {name} is not a decimal integer") from exc
        records.append(record)
    if not records:
        raise ValueError("no RESULT records found")
    return records


def _load_context(path, mode, observed_bytes):
    if path is None:
        if mode == "baseline":
            return {
                "label": "baseline-no-crypto",
                "key": None,
                "nonce": None,
                "counter": 0,
                "context_id": None,
            }
        return {
            "label": "public-bringup",
            "key": PUBLIC_KEY,
            "nonce": PUBLIC_NONCE,
            "counter": PUBLIC_COUNTER,
            "context_id": None,
        }

    try:
        context = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read context: {path}") from exc
    context_mode, key, nonce, counter = validate_context(context)
    expected_mode = "baseline" if mode == "baseline" else "aes-128-ctr"
    if context_mode != expected_mode:
        raise ValueError(
            f"context mode {context_mode!r} does not match log mode {mode!r}")
    if context["bytes"] != observed_bytes:
        raise ValueError(
            f"context plans {context['bytes']} bytes, log contains {observed_bytes}")
    return {
        "label": "private-context",
        "key": key if mode == "secure" else None,
        "nonce": nonce if mode == "secure" else None,
        "counter": counter,
        "context_id": context.get("context_id"),
    }


def verify(records, mode, expected_vector=DEFAULT_VECTOR, minimum_trials=4,
           context_path=None):
    """Verify parsed records and return a serializable evidence report."""
    if mode not in ("baseline", "secure"):
        raise ValueError("mode must be baseline or secure")
    if not expected_vector:
        raise ValueError("expected vector cannot be empty")
    if minimum_trials <= 0:
        raise ValueError("minimum trials must be positive")

    failures = []
    if len(records) < minimum_trials:
        failures.append(
            f"only {len(records)} trials; at least {minimum_trials} required")

    expected_sequence = 1
    ciphertext = bytearray()
    transmitted = bytearray()
    host_windows = []
    for record in records:
        sequence = record["seq"]
        if sequence != expected_sequence:
            failures.append(
                f"line {record['line']}: seq={sequence}, expected {expected_sequence}")
            expected_sequence = sequence
        expected_sequence += 1

        if record["mode"] != mode:
            failures.append(
                f"line {record['line']}: mode={record['mode']}, expected {mode}")
        if record["tx"] != expected_vector:
            failures.append(
                f"line {record['line']}: unexpected TX {record['tx'].hex().upper()}")
        if record["rx_len"] != len(record["rx"]):
            failures.append(
                f"line {record['line']}: rx_len={record['rx_len']} but log has "
                f"{len(record['rx'])} bytes")
        if len(record["rx"]) != len(expected_vector):
            failures.append(
                f"line {record['line']}: expected {len(expected_vector)} RX bytes, "
                f"got {len(record['rx'])}")
        for field in ERROR_FIELDS:
            if record[field] != 0:
                failures.append(
                    f"line {record['line']}: {field}={record[field]}")
        if record["host_window_us"] <= 0:
            failures.append(
                f"line {record['line']}: non-positive host_window_us")

        transmitted.extend(record["tx"])
        ciphertext.extend(record["rx"])
        host_windows.append(record["host_window_us"])

    context = _load_context(context_path, mode, len(ciphertext))
    if mode == "secure":
        recovered = crypt(
            context["key"], context["nonce"], context["counter"],
            bytes(ciphertext))
    else:
        recovered = bytes(ciphertext)

    if recovered != bytes(transmitted):
        mismatch = next(
            (index for index, pair in enumerate(zip(recovered, transmitted))
             if pair[0] != pair[1]),
            min(len(recovered), len(transmitted)),
        )
        failures.append(f"recovered stream diverges at byte offset {mismatch}")

    if mode == "baseline":
        for record in records:
            if record["same"] != 1:
                failures.append(
                    f"line {record['line']}: baseline same={record['same']}")

    context_report = {
        "label": context["label"],
        "context_id": context["context_id"],
        "initial_counter": context["counter"],
    }
    if context["key"] is not None:
        context_report.update({
            "key_sha256": hashlib.sha256(context["key"]).hexdigest(),
            "nonce_hex": context["nonce"].hex(),
        })

    return {
        "status": "PASS" if not failures else "FAIL",
        "mode": mode,
        "trials": len(records),
        "bytes": len(ciphertext),
        "sequence_first": records[0]["seq"],
        "sequence_last": records[-1]["seq"],
        "stimulus_hex": expected_vector.hex().upper(),
        "received_hex": bytes(ciphertext).hex().upper(),
        "received_sha256": hashlib.sha256(ciphertext).hexdigest(),
        "recovered_sha256": hashlib.sha256(recovered).hexdigest(),
        "host_window_us_min": min(host_windows),
        "host_window_us_max": max(host_windows),
        "context": context_report,
        "failures": failures,
        "note": (
            "host_window_us is ESP32 driver/RTOS timing, not FPGA latency; "
            "oscilloscope evidence is required for RX-to-TX latency."
        ),
    }


def _write_private_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True,
                        help="saved idf.py monitor transcript")
    parser.add_argument("--mode", choices=("baseline", "secure"), required=True)
    parser.add_argument("--context", type=Path,
                        help="private context JSON; omit only for public bring-up")
    parser.add_argument("--expected-hex", default=DEFAULT_VECTOR.hex())
    parser.add_argument("--min-trials", type=int, default=4)
    parser.add_argument("--report", type=Path,
                        help="new JSON evidence file; existing files are refused")
    args = parser.parse_args()

    try:
        expected = _hex_bytes(args.expected_hex, "expected-hex")
        input_text = args.input.read_text(encoding="utf-8", errors="replace")
        records = parse_results(input_text)
        result = verify(records, args.mode, expected, args.min_trials,
                        args.context)
        result["input_sha256"] = hashlib.sha256(
            args.input.read_bytes()).hexdigest()
        if args.report is not None:
            _write_private_json(args.report, result)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
