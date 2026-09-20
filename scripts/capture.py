#!/usr/bin/env python3
"""Linux 9600/8N1 binary capture and independent baseline/AES-CTR comparison.

This utility does NOT provision or arm the FPGA. Start both input/output
recorders before enabling a replay with matching FPGA configuration.
Private context files and GPS captures must stay outside version control.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
import sys
import termios
import time

from ctr_vectors import crypt


def private_file(path, binary=False):
    """Create exclusively with private permissions; never overwrite captures."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return os.fdopen(fd, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"}))


def compare(reference, received, context, invalid_reasons=()):
    if not isinstance(context, dict):
        raise ValueError("Context must be a JSON object")
    mode = context.get("mode")
    count = context.get("bytes")
    if type(count) is not int or count <= 0:
        raise ValueError("Context bytes must be a positive integer")
    if mode not in ("baseline", "aes-128-ctr"):
        raise ValueError("Context mode must be baseline or aes-128-ctr")
    if mode == "aes-128-ctr":
        if not all(isinstance(context.get(field), str) for field in ("key_hex", "nonce_hex")):
            raise ValueError("key_hex and nonce_hex must be hexadecimal strings")
        key = bytes.fromhex(context["key_hex"])
        nonce = bytes.fromhex(context["nonce_hex"])
        counter = context["initial_counter"]
        if type(counter) is not int:
            raise ValueError("initial_counter must be an integer")
        # Validate the planned length even if the actual capture is truncated.
        if not 0 <= counter <= 0xffffffff or (count + 15) // 16 > (1 << 32) - counter:
            raise ValueError("Capture would exceed the 32-bit counter")
        recovered = crypt(key, nonce, counter, received)
    else:
        recovered = received
    mismatch = next((i for i, (a, b) in enumerate(zip(reference, recovered)) if a != b), None)
    if mismatch is None and len(reference) != len(recovered):
        mismatch = min(len(reference), len(recovered))
    valid = (len(reference) == len(received) == count and mismatch is None and not invalid_reasons)
    report = {
        "status": "PASS" if valid else "FAIL", "mode": mode, "expected_bytes": count,
        "reference_bytes": len(reference), "received_bytes": len(received),
        "missing_received_bytes": max(0, count - len(received)),
        "extra_received_bytes": max(0, len(received) - count),
        "first_divergence_offset": mismatch, "invalid_reasons": list(invalid_reasons),
        "reference_sha256": hashlib.sha256(reference).hexdigest(),
        "received_sha256": hashlib.sha256(received).hexdigest(),
        "recovered_sha256": hashlib.sha256(recovered).hexdigest(),
        "note": "Byte comparison only; CTR does not authenticate data. No FPGA latency is measured here.",
    }
    return report, recovered


def record_serial(port, output, count, timeout, ready=None):
    if type(count) is not int or count <= 0 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Capture length and timeout must be positive")
    fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    previous = None
    started = time.monotonic()
    digest, received, error = hashlib.sha256(), 0, None
    try:
        with private_file(output, binary=True) as stream:
            # Reserve output before changing/flushing a port; a filename
            # collision must not discard bytes already waiting in its queue.
            previous = termios.tcgetattr(fd)
            config = termios.tcgetattr(fd)
            config[0] = 0  # Binary input: no XON/XOFF, CR/LF translation or stripping.
            config[1] = 0
            config[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            config[3] = 0
            config[4] = config[5] = termios.B9600
            config[6][termios.VMIN] = 0
            config[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, config)
            termios.tcflush(fd, termios.TCIFLUSH)
            started = time.monotonic()
            deadline = started + timeout
            if ready:
                ready()
            while received < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    error = "timeout"
                    break
                if not select.select([fd], [], [], remaining)[0]:
                    error = "timeout"
                    break
                try:
                    chunk = os.read(fd, min(4096, count - received))
                except BlockingIOError:
                    continue
                if not chunk:
                    error = "serial input closed"
                    break
                stream.write(chunk)
                digest.update(chunk)
                received += len(chunk)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        try:
            if previous is not None:
                termios.tcsetattr(fd, termios.TCSANOW, previous)
        finally:
            os.close(fd)
    return {
        "status": "CAPTURED" if received == count else "INCOMPLETE",
        "port": str(port), "format": "9600/8N1", "expected_bytes": count,
        "received_bytes": received, "sha256": digest.hexdigest(), "error": error,
        "host_elapsed_seconds": time.monotonic() - started,
        "note": "Host acquisition time, not FPGA latency. CAPTURED is not byte verification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record", help="Read exactly N binary bytes; preserve partial capture on timeout")
    record.add_argument("--port", required=True)
    record.add_argument("--output", type=Path, required=True)
    record.add_argument("--bytes", type=int, required=True)
    record.add_argument("--timeout", type=float, required=True, help="Overall deadline in seconds")
    record.add_argument("--report", type=Path, required=True)
    verify = commands.add_parser("compare", help="Compare previously captured binary files")
    verify.add_argument("--reference", type=Path, required=True)
    verify.add_argument("--received", type=Path, required=True)
    verify.add_argument("--context", type=Path, required=True)
    verify.add_argument("--report", type=Path, required=True)
    verify.add_argument("--recovered", type=Path, required=True)
    verify.add_argument("--invalid", action="append", default=[], help="Invalidate for observed reset/framing/overflow etc.")
    args = parser.parse_args()
    try:
        if args.command == "record":
            # Reserve the report before touching the serial port or capture.
            with private_file(args.report) as report_file:
                try:
                    result = record_serial(args.port, args.output, args.bytes, args.timeout,
                                           ready=lambda: print("READY: start the configured replay now", flush=True))
                except Exception as exc:
                    json.dump({"status": "ERROR", "error": str(exc)}, report_file, indent=2)
                    raise
                json.dump(result, report_file, indent=2)
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "CAPTURED" else 1
        context = json.loads(args.context.read_text(encoding="utf-8"))
        result, recovered = compare(args.reference.read_bytes(), args.received.read_bytes(), context, args.invalid)
        with private_file(args.report) as report_file:
            with private_file(args.recovered, binary=True) as recovered_file:
                recovered_file.write(recovered)
            json.dump(result, report_file, indent=2)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, termios.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
