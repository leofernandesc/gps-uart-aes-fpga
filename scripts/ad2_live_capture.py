#!/usr/bin/env python3
"""P14: input-only AD2 DigitalIn Record + CP2102, with no byte realignment.

GPS must be inactive until READY. DIO0 observes GPS TX / FPGA V10; DIO1
observes FPGA W10; CP2102 RX observes W10, TX disconnected; common GND.
Close WaveForms first. Acquisition is not PASS until offline comparison AND
the operator's no-reset/no-overflow/no-framing observations are confirmed.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
from ctypes import CDLL, byref, c_double, c_int, c_ubyte, create_string_buffer
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import select
import sys
import termios
import time

from build_manifest import digest, verify
from capture import compare, private_file
from context import claim_capture, validate_context
from gps_fixture import parse_window
from serial_bench import _configure


class UARTDecoder:
    """Incremental center-sampled 8N1 decoder; run scans execute in C.

    Require a full initial idle bit. Frame starts are absolute sample indices.
    A malformed stop is an error, never an alignment hint or deleted byte.
    """
    def __init__(self, rate, baud=38400, bit=0, limit=None):
        if not math.isfinite(rate) or rate / baud < 16 or bit not in range(8):
            raise ValueError("decoder requires >=16 samples/bit and a bit in [0,7]")
        self.period = rate / baud
        self.table = bytes((value >> bit) & 1 for value in range(256))
        self.limit = limit
        self.offset = 0
        self.previous = None
        self.high_since = 0
        self.start = None
        self.stage = 0
        self.value = 0
        self.data = bytearray()
        self.starts = []
        self.framing_errors = 0
        self.false_starts = 0

    def feed(self, samples):
        levels = samples.translate(self.table)
        for run in re.finditer(b"\x00+|\x01+", levels):
            a, b = self.offset + run.start(), self.offset + run.end()
            level = levels[run.start()]
            if self.limit is not None and len(self.data) >= self.limit:
                break
            if level != self.previous:
                if level:
                    self.high_since = a
                elif self.previous == 1 and self.start is None and a - self.high_since >= math.floor(self.period):
                    self.start, self.stage, self.value = a, 0, 0
                self.previous = level
            while self.start is not None:
                sample = math.floor(self.start + (self.stage + 0.5) * self.period)
                if sample >= b:
                    break
                if self.stage == 0 and level:
                    self.false_starts += 1
                    self.start = None
                    break
                if 1 <= self.stage <= 8:
                    self.value |= level << (self.stage - 1)
                if self.stage == 9:
                    if level:
                        self.data.append(self.value)
                        self.starts.append(self.start)
                    else:
                        self.framing_errors += 1
                    self.start = None
                    break
                self.stage += 1
        self.offset += len(samples)


def assess(reference, cipher, serial, context, acquisition):
    invalid = list(acquisition.get("invalid_reasons", []))
    for field in ("lost_samples", "corrupt_samples", "reference_framing_errors", "cipher_framing_errors",
                  "reference_false_starts", "cipher_false_starts"):
        if acquisition.get(field) != 0:
            invalid.append(f"{field} not zero/available")
    if acquisition.get("ready_idle_verified") is not True:
        invalid.append("initial common idle not verified")
    if serial != cipher or len(serial) != context["bytes"]:
        invalid.append("CP2102 differs from AD2 output or is incomplete")
    report, recovered = compare(reference, cipher, context, invalid)
    for label, payload in (("reference", reference), ("recovered", recovered)):
        try:
            sentences, start, end = parse_window(payload)
            report[label + "_nmea"] = {"sentences": len(sentences),
                "types": dict(Counter(s[1:6] for s in sentences)),
                "prefix_bytes": start, "suffix_bytes": len(payload) - end}
        except ValueError as exc:
            report["invalid_reasons"].append(f"{label} NMEA: {exc}")
            report["status"] = "FAIL"
    report["cp2102_sha256"] = hashlib.sha256(serial).hexdigest()
    return report, recovered


def checked(dwf, name, *args):
    if getattr(dwf, name)(*args) == 0:
        message = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(message)
        raise RuntimeError(f"{name}: {message.value.decode(errors='replace')}")


def record(a):
    if not a.confirm_source_inactive or not a.confirm_txd_disconnected:
        raise ValueError("confirm GPS inactive until READY and CP2102 TXD disconnected")
    if not 614400 <= a.rate <= 2000000 or not math.isfinite(a.timeout) or a.timeout <= 0:
        raise ValueError("rate must be 614400..2000000 Hz and timeout positive")
    context = json.loads(a.context.read_text())
    validate_context(context)
    manifest = verify(a.build)
    binding = json.loads((a.build / "context-binding.json").read_text())
    if binding["context_sha256"] != digest(a.context) or binding["context_id"] != context["context_id"]:
        raise ValueError("context does not match experiment build")
    if manifest["design"] != ("secure" if context["mode"] == "aes-128-ctr" else "baseline"):
        raise ValueError("build mode mismatch")
    a.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": 1, "status": "RUNNING", "created_utc": datetime.now(timezone.utc).isoformat(),
              "context_sha256": digest(a.context), "context_id": context["context_id"],
              "sof_sha256": manifest["artifacts_sha256"][f"uart_{manifest['design']}.sof"],
              "programming_note": "SOF identity bound here; successful JTAG programming must be retained separately",
              "baud": 38400, "expected_bytes": context["bytes"], "requested_sample_rate_hz": a.rate,
              "lost_samples": 0, "corrupt_samples": 0, "ready_idle_verified": False, "invalid_reasons": [],
              "note": "AD2 input-only Record, DIO0=reference, DIO1=output. No search/byte trimming for alignment."}
    # Once hardware acquisition might begin, consume even on abort/failure.
    report["claim"] = claim_capture(context, a.registry)
    dwf, handle = None, c_int()
    decoders = []
    serial = bytearray()
    started = time.monotonic()
    samples_total = 0
    try:
        with ExitStack() as stack:
            raw = stack.enter_context(private_file(a.output / "samples.bin", True))
            fd = os.open(a.port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
            stack.callback(os.close, fd)
            previous = termios.tcgetattr(fd)
            stack.callback(termios.tcsetattr, fd, termios.TCSANOW, previous)
            _configure(fd, 38400)
            dwf = CDLL("libdwf.so")
            devices = c_int()
            checked(dwf, "FDwfEnum", c_int(0), byref(devices))
            if not 0 <= a.device_index < devices.value:
                raise ValueError("AD2 device index not available")
            checked(dwf, "FDwfDeviceOpen", c_int(a.device_index), byref(handle))
            if not handle.value:
                raise RuntimeError("AD2 unavailable; close WaveForms")
            device, revision = c_int(), c_int()
            checked(dwf, "FDwfEnumDeviceType", c_int(a.device_index), byref(device), byref(revision))
            if device.value != 3:
                raise ValueError("selected instrument is not Analog Discovery 2")
            checked(dwf, "FDwfDeviceAutoConfigureSet", handle, c_int(0))
            for i in range(16):
                checked(dwf, "FDwfDigitalOutEnableSet", handle, c_int(i), c_int(0))
            checked(dwf, "FDwfDigitalOutConfigure", handle, c_int(0))
            checked(dwf, "FDwfDigitalIOOutputEnableSet", handle, c_int(0))
            checked(dwf, "FDwfDigitalIOConfigure", handle)
            hz = c_double()
            checked(dwf, "FDwfDigitalInInternalClockInfo", handle, byref(hz))
            divider = max(1, round(hz.value / a.rate))
            rate = hz.value / divider
            report["sample_rate_hz"] = rate
            report["sample_format"] = "unsigned 8-bit, DIO0 bit0 / DIO1 bit1"
            decoders = [UARTDecoder(rate, bit=i, limit=context["bytes"]) for i in (0, 1)]
            checked(dwf, "FDwfDigitalInAcquisitionModeSet", handle, c_int(3))
            checked(dwf, "FDwfDigitalInDividerSet", handle, c_int(divider))
            checked(dwf, "FDwfDigitalInSampleFormatSet", handle, c_int(8))
            checked(dwf, "FDwfDigitalInTriggerSourceSet", handle, c_ubyte(0))
            checked(dwf, "FDwfDigitalInTriggerPositionSet", handle, c_int(0))
            checked(dwf, "FDwfDigitalInConfigure", handle, c_int(0), c_int(1))
            ready_at = None
            started = time.monotonic()
            while time.monotonic() - started < a.timeout:
                state, available, lost, corrupt = c_ubyte(), c_int(), c_int(), c_int()
                checked(dwf, "FDwfDigitalInStatus", handle, c_int(1), byref(state))
                checked(dwf, "FDwfDigitalInStatusRecord", handle, byref(available), byref(lost), byref(corrupt))
                report["lost_samples"] += lost.value
                report["corrupt_samples"] += corrupt.value
                if lost.value or corrupt.value:
                    raise ValueError("AD2 sample loss/corruption; run invalid, reduce rate")
                if available.value:
                    buffer = (c_ubyte * available.value)()
                    checked(dwf, "FDwfDigitalInStatusData2", handle, buffer, c_int(0), c_int(available.value))
                    chunk = bytes(buffer)
                    raw.write(chunk)
                    samples_total += len(chunk)
                    if ready_at is None:
                        if any((value & 3) != 3 for value in chunk):
                            raise ValueError("UART activity/non-idle before READY; keep GPS inactive")
                    for decoder in decoders:
                        decoder.feed(chunk)
                if select.select([fd], [], [], 0)[0]:
                    data = os.read(fd, 4096)
                    if ready_at is None and data:
                        raise ValueError("CP2102 received bytes before READY")
                    serial.extend(data[:max(0, context["bytes"] - len(serial))])
                if ready_at is None and samples_total >= math.ceil(rate * 0.25):
                    ready_at = time.monotonic()
                    report["ready_idle_verified"] = True
                    report["ready_sample_offset"] = samples_total
                    print("READY: AD2 + CP2102 armed; enable GPS now. Do not press KEY0.", flush=True)
                if ready_at is not None and all(len(d.data) == context["bytes"] for d in decoders) and len(serial) == context["bytes"]:
                    report["status"] = "CAPTURED"
                    break
                # Frequent polls keep the AD2 Record buffer drained.
                time.sleep(0.001)
            if report["status"] != "CAPTURED":
                report["invalid_reasons"].append("timeout/incomplete capture")
                report["status"] = "FAIL"
    except (OSError, ValueError, RuntimeError, KeyboardInterrupt) as exc:
        report["invalid_reasons"].append(str(exc) or "interrupted")
        report["status"] = "FAIL"
    finally:
        if dwf is not None and handle.value:
            dwf.FDwfDigitalInConfigure(handle, c_int(0), c_int(0))
            dwf.FDwfDeviceClose(handle)
        report["host_elapsed_seconds"] = time.monotonic() - started
        report["samples"] = samples_total
        for label, decoder in zip(("reference", "cipher"), decoders):
            report[label + "_framing_errors"] = decoder.framing_errors
            report[label + "_false_starts"] = decoder.false_starts
            report[label + "_frame_start_samples"] = decoder.starts
            with private_file(a.output / (label + ".bin"), True) as stream:
                stream.write(decoder.data)
        with private_file(a.output / "cp2102.bin", True) as stream:
            stream.write(serial)
        for name in ("samples.bin", "reference.bin", "cipher.bin", "cp2102.bin"):
            if (a.output / name).is_file():
                report.setdefault("artifacts_sha256", {})[name] = digest(a.output / name)
        with private_file(a.output / "acquisition.json") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps({"status": report["status"], "output": str(a.output),
                      "invalid_reasons": report["invalid_reasons"]}, indent=2))
    return 0 if report["status"] == "CAPTURED" else 1


def analyze(a):
    context = json.loads(a.context.read_text())
    validate_context(context)
    acquisition = json.loads((a.input / "acquisition.json").read_text())
    if acquisition["context_sha256"] != digest(a.context):
        raise ValueError("analysis context changed")
    for name, value in acquisition["artifacts_sha256"].items():
        if Path(name).name != name or digest(a.input / name) != value:
            raise ValueError("acquisition artifact modified/unsafe path")
    data = [(a.input / name).read_bytes() for name in ("reference.bin", "cipher.bin", "cp2102.bin")]
    report, recovered = assess(*data, context, acquisition)
    observations = {"overflow_off": a.confirm_led6_off, "framing_off": a.confirm_led7_off,
                    "no_reset": a.confirm_no_reset}
    if not all(observations.values()):
        report["invalid_reasons"].append("operator observations incomplete")
        report["status"] = "FAIL"
    report["operator_observations"] = observations
    report["acquisition_sha256"] = digest(a.input / "acquisition.json")
    report["physical_latency_note"] = "1-us nominal digital resolution; not an 80-ns AES latency measurement"
    with ExitStack() as stack:
        stream = stack.enter_context(private_file(a.input / "comparison.json"))
        output = stack.enter_context(private_file(a.input / "recovered.bin", True))
        output.write(recovered)
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    r = sub.add_parser("record")
    r.add_argument("--port", required=True)
    r.add_argument("--context", type=Path, required=True)
    r.add_argument("--registry", type=Path)
    r.add_argument("--build", type=Path, required=True)
    r.add_argument("--output", type=Path, required=True)
    r.add_argument("--rate", type=int, default=1000000)
    r.add_argument("--timeout", type=float, default=90)
    r.add_argument("--device-index", type=int, default=0)
    r.add_argument("--confirm-source-inactive", action="store_true")
    r.add_argument("--confirm-txd-disconnected", action="store_true")
    s = sub.add_parser("analyze")
    s.add_argument("--input", type=Path, required=True)
    s.add_argument("--context", type=Path, required=True)
    for flag in ("led6-off", "led7-off", "no-reset"):
        s.add_argument("--confirm-" + flag, action="store_true")
    a = p.parse_args()
    try:
        return record(a) if a.action == "record" else analyze(a)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"FAIL P14: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
