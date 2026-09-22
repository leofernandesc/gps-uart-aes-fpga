#!/usr/bin/env python3
"""Run the physical UART bench through one PC USB-TTL adapter.

The CP2102 is the only external host in the current bench. It opens one
full-duplex 9600/8N1 port, sends a known stimulus or a previously captured GPS
stream, records the FPGA response, and compares it independently on the PC.
This utility does not provision the FPGA: program the selected baseline or
secure SOF first and use a fresh context for every secure capture.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import select
import sys
import termios
import time

from capture import compare, private_file
from context import claim_capture, validate_context


FORMAT = "9600/8N1"


def _timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_context(path):
    try:
        context = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read context: {path}") from exc
    validate_context(context)
    return context


def _reserve_files(output, report):
    """Reserve both private files, removing newly created files on collision."""
    paths = [Path(output), Path(report)]
    if paths[0] == paths[1]:
        raise ValueError("received output and report must be different files")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    streams = []
    try:
        streams.append((paths[0], private_file(paths[0], binary=True)))
        streams.append((paths[1], private_file(paths[1])))
    except Exception:
        for path, stream in reversed(streams):
            stream.close()
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    return streams[0][1], streams[1][1]


def _configure(fd):
    previous = termios.tcgetattr(fd)
    config = termios.tcgetattr(fd)
    config[0] = config[1] = config[3] = 0
    config[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    config[4] = config[5] = termios.B9600
    config[6][termios.VMIN] = config[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, config)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return previous


def _write_all(fd, payload, timeout):
    deadline = time.monotonic() + timeout
    offset = 0
    while offset < len(payload):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise TimeoutError("timeout while sending serial stimulus")
        try:
            offset += os.write(fd, payload[offset:])
        except BlockingIOError:
            continue
    return offset


def _read_response(fd, expected, timeout, guard):
    """Read one response and detect bytes beyond its expected boundary."""
    received = bytearray()
    deadline = time.monotonic() + timeout
    timed_out = False
    while len(received) < expected:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            timed_out = True
            break
        try:
            chunk = os.read(fd, expected - len(received))
        except BlockingIOError:
            continue
        if not chunk:
            timed_out = True
            break
        received.extend(chunk)

    extra = bytearray()
    if not timed_out and guard:
        guard_deadline = time.monotonic() + guard
        while True:
            remaining = guard_deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                break
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if not chunk:
                break
            extra.extend(chunk)
    return bytes(received), bytes(extra), timed_out


def _transaction(fd, payload, timeout, guard, output):
    started = time.monotonic()
    _write_all(fd, payload, timeout)
    response, extra, timed_out = _read_response(fd, len(payload), timeout, guard)
    output.write(response)
    output.write(extra)
    output.flush()
    return {
        "tx_hex": payload.hex(" ").upper(),
        "tx_bytes": len(payload),
        "rx_hex": (response + extra).hex(" ").upper(),
        "rx_bytes": len(response) + len(extra),
        "missing_bytes": max(0, len(payload) - len(response)),
        "extra_bytes": len(extra),
        "timeout": timed_out,
        "elapsed_seconds": time.monotonic() - started,
    }, response + extra


def _run(port, transactions, context, registry, output, timeout, guard, interval):
    claimed = claim_capture(context, registry if context.get("mode") == "aes-128-ctr" else None)
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    previous = None
    records = []
    received = bytearray()
    invalid = []
    started = time.monotonic()
    try:
        previous = _configure(fd)
        print(f"READY: CP2102 armed on {port}; send/replay may start now", flush=True)
        for index, payload in enumerate(transactions):
            try:
                record, response = _transaction(fd, payload, timeout, guard, output)
            except (OSError, TimeoutError) as exc:
                invalid.append(f"tx_{index}: {exc}")
                records.append({
                    "tx_hex": payload.hex(" ").upper(),
                    "tx_bytes": len(payload),
                    "rx_hex": "",
                    "rx_bytes": 0,
                    "missing_bytes": len(payload),
                    "extra_bytes": 0,
                    "timeout": isinstance(exc, TimeoutError),
                    "error": str(exc),
                })
                break
            records.append(record)
            received.extend(response)
            if record["timeout"]:
                invalid.append(f"tx_{index}: timeout")
                break
            if record["missing_bytes"]:
                invalid.append(f"tx_{index}: missing_response_bytes")
            if record["extra_bytes"]:
                invalid.append(f"tx_{index}: extra_response_bytes")
            if index + 1 < len(transactions) and interval:
                time.sleep(interval)
    finally:
        try:
            if previous is not None:
                termios.tcsetattr(fd, termios.TCSANOW, previous)
        finally:
            os.close(fd)
    return claimed, records, bytes(received), invalid, time.monotonic() - started


def _build_result(operation, port, context, claimed, transactions, received,
                  reference, invalid, elapsed):
    comparison, recovered = compare(reference, received, context, invalid)
    return {
        "status": comparison["status"],
        "created_utc": _timestamp(),
        "operation": operation,
        "port": str(port),
        "format": FORMAT,
        "mode": context["mode"],
        "expected_bytes": context["bytes"],
        "received_bytes": len(received),
        "transactions": transactions,
        "context_claim": claimed,
        "invalid_reasons": invalid,
        "host_elapsed_seconds": elapsed,
        "comparison": comparison,
        "received_sha256": comparison["received_sha256"],
        "recovered_sha256": comparison["recovered_sha256"],
        "note": (
            "One CP2102 full-duplex host at 9600/8N1. Host timing includes the "
            "Linux driver and USB bridge; it is not FPGA latency. The adapter "
            "does not expose FPGA framing flags; use the FPGA diagnostics and "
            "oscilloscope/AD2 for electrical evidence."
        ),
        "recovered_bytes": len(recovered),
    }


def _parse_stimulus(value):
    try:
        payload = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("stimulus must be hexadecimal bytes") from exc
    if not payload:
        raise ValueError("stimulus must contain at least one byte")
    return payload


def _execute(args, operation, payloads, reference):
    context = _load_context(args.context)
    if context["bytes"] != len(reference):
        raise ValueError(
            f"context bytes={context['bytes']} does not match the planned payload "
            f"({len(reference)} bytes)"
        )
    if context["mode"] == "aes-128-ctr" and not args.registry:
        raise ValueError("secure operation requires --registry")
    if args.timeout <= 0 or not math.isfinite(args.timeout):
        raise ValueError("--timeout must be finite and positive")
    if args.response_guard < 0 or not math.isfinite(args.response_guard):
        raise ValueError("--response-guard must be finite and non-negative")
    if args.interval < 0 or not math.isfinite(args.interval):
        raise ValueError("--interval must be finite and non-negative")

    output_stream, report_stream = _reserve_files(args.received, args.report)
    with output_stream, report_stream:
        try:
            claimed, transactions, received, invalid, elapsed = _run(
                args.port, payloads, context, args.registry, output_stream,
                args.timeout, args.response_guard, args.interval
            )
            result = _build_result(operation, args.port, context, claimed,
                                   transactions, received, reference, invalid, elapsed)
        except Exception as exc:
            result = {
                "status": "ERROR",
                "created_utc": _timestamp(),
                "operation": operation,
                "port": str(args.port),
                "format": FORMAT,
                "mode": context["mode"],
                "error": str(exc),
                "note": "A secure context is consumed before READY and must not be reused after a failed attempt.",
            }
            json.dump(result, report_stream, indent=2)
            report_stream.write("\n")
            raise
        json.dump(result, report_stream, indent=2)
        report_stream.write("\n")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--port", required=True, help="CP2102 port, e.g. /dev/ttyUSB0")
    common.add_argument("--context", type=Path, required=True)
    common.add_argument("--registry", type=Path, help="nonce registry for secure contexts")
    common.add_argument("--received", type=Path, required=True, help="private binary response")
    common.add_argument("--report", type=Path, required=True, help="private JSON report")
    common.add_argument("--timeout", type=float, default=1.0,
                        help="per-transaction response deadline in seconds")
    common.add_argument("--response-guard", type=float, default=0.010,
                        help="time used to detect response bytes beyond the frame")
    common.add_argument("--interval", type=float, default=0.050,
                        help="pause between known-stimulus transactions")

    run = commands.add_parser("run", parents=[common],
                              help="send a known vector repeatedly and verify responses")
    run.add_argument("--stimulus-hex", default="55 A5 00 FF 3C")
    run.add_argument("--trials", type=int, default=4)

    replay = commands.add_parser("replay", parents=[common],
                                 help="replay a captured GPS stream and verify the response")
    replay.add_argument("--input", type=Path, required=True,
                        help="private GPS/reference binary to transmit")

    args = parser.parse_args()
    try:
        if args.command == "run":
            if args.trials <= 0:
                raise ValueError("--trials must be positive")
            stimulus = _parse_stimulus(args.stimulus_hex)
            reference = stimulus * args.trials
            return _execute(args, "known-stimulus", [stimulus] * args.trials, reference)
        payload = args.input.read_bytes()
        if not payload:
            raise ValueError("replay input is empty")
        args.interval = 0.0
        return _execute(args, "gps-replay", [payload], payload)
    except (OSError, ValueError, KeyError, termios.error, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
