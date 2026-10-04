#!/usr/bin/env python3
"""P14: input-only AD2 DigitalIn Record + CP2102, with no byte realignment.

GPS must be inactive until READY. DIO0 observes GPS TX / FPGA V10; --tx-dio
selects the AD2 digital line observing FPGA W10 (default DIO1); CP2102 RX also
observes W10, TX disconnected; common GND. Close WaveForms first. Acquisition
is not PASS until offline comparison AND the operator's no-reset/no-overflow/
no-framing observations are confirmed.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
from ctypes import CDLL, byref, c_double, c_int, c_uint, c_ubyte, create_string_buffer, string_at
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from queue import Empty, Full, Queue
import re
import select
import sys
import termios
from threading import Event, Thread
import time

from build_manifest import digest, verify
from capture import compare, private_file
from context import claim_capture, validate_context
from gps_fixture import parse_window
from live_timing import frame_metrics
from serial_bench import _configure


class UARTDecoder:
    """Incremental center-sampled 8N1 decoder; run scans execute in C.

    Require a full initial idle bit. Frame starts are absolute sample indices.
    A malformed stop is an error, never an alignment hint or deleted byte.
    """
    def __init__(self, rate, baud=9600, bit=0, limit=None):
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


class CommonIdlePreflight:
    """Retain startup samples, then require 250 ms of strictly common idle.

    The first 20 ms belong to instrument stabilization, not the measurement
    window. UART activity recognized even in that interval invalidates arming.
    No samples/bytes after stabilization can be ignored or realigned.
    """
    def __init__(self, rate, baud, tx_dio, report):
        self.warmup_limit = math.ceil(rate * 0.020)
        self.idle_target = math.ceil(rate * 0.250)
        self.warmup_seen = self.idle_seen = 0
        mask = 1 | (1 << tx_dio)
        self.idle_table = bytes(int(value & mask != mask) for value in range(256))
        self.decoders = [UARTDecoder(rate, baud=baud, bit=i) for i in (0, tx_dio)]
        self.report = report
        report.update({"instrument_warmup_seconds": 0.020,
                       "instrument_warmup_samples": 0,
                       "instrument_warmup_non_idle_samples": 0,
                       "required_common_idle_seconds": 0.250,
                       "verified_common_idle_samples": 0,
                       "decode_start_sample": self.warmup_limit})

    @property
    def ready(self):
        return self.idle_seen >= self.idle_target

    def feed(self, chunk):
        count = min(len(chunk), self.warmup_limit - self.warmup_seen)
        warmup, idle = chunk[:count], chunk[count:]
        if warmup:
            self.warmup_seen += count
            self.report["instrument_warmup_samples"] = self.warmup_seen
            self.report["instrument_warmup_non_idle_samples"] += warmup.translate(self.idle_table).count(1)
            for decoder in self.decoders:
                decoder.feed(warmup)
            self.report["instrument_warmup_uart_frames"] = [len(d.data) for d in self.decoders]
            self.report["instrument_warmup_framing_errors"] = [d.framing_errors for d in self.decoders]
            self.report["instrument_warmup_false_starts"] = [d.false_starts for d in self.decoders]
            if any(d.data or d.start is not None or d.framing_errors or d.false_starts
                   for d in self.decoders):
                raise ValueError("UART activity during instrument stabilization; keep GPS inactive")
        if idle:
            if idle.translate(self.idle_table).count(1):
                self.report["pre_ready_sample_count"] = len(idle)
                self.report["pre_ready_sample_values"] = {
                    f"0x{value:02X}": count for value, count in Counter(idle).most_common()}
                raise ValueError("UART activity/non-idle before READY; keep GPS inactive")
            self.idle_seen += len(idle)
            self.report["verified_common_idle_samples"] = self.idle_seen
        return idle


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


def sample_divider(clock, requested, baud=9600):
    """Choose the nearest divider without rounding below 16 samples/bit."""
    maximum = math.floor(clock / (16 * baud))
    if maximum < 1:
        raise ValueError("instrument clock cannot provide 16 samples/bit")
    return max(1, min(round(clock / requested), maximum))


def open_record_device(dwf, device_index, handle, report):
    """Choose the enumerated configuration with the largest DigitalIn RAM."""
    count = c_int()
    checked(dwf, "FDwfEnumConfig", c_int(device_index), byref(count))
    configurations = []
    for index in range(count.value):
        channels, size = c_int(), c_int()
        checked(dwf, "FDwfEnumConfigInfo", c_int(index), c_int(4), byref(channels))
        checked(dwf, "FDwfEnumConfigInfo", c_int(index), c_int(9), byref(size))
        configurations.append({"index": index, "digital_input_channels": channels.value,
                               "digital_input_buffer_samples": size.value})
    eligible = [c for c in configurations if c["digital_input_channels"] >= 8
                and c["digital_input_buffer_samples"] > 0]
    if not eligible:
        raise ValueError("AD2 has no suitable DigitalIn device configuration")
    selected = max(eligible, key=lambda c: c["digital_input_buffer_samples"])
    report["device_configurations"] = configurations
    report["device_configuration_index"] = selected["index"]
    checked(dwf, "FDwfDeviceConfigOpen", c_int(device_index), c_int(selected["index"]),
            byref(handle))
    if not handle.value:
        raise RuntimeError("AD2 unavailable; close WaveForms")


def configure_record_buffer(dwf, handle, rate, report):
    maximum, before, actual = c_int(), c_int(), c_int()
    checked(dwf, "FDwfDigitalInBufferSizeInfo", handle, byref(maximum))
    checked(dwf, "FDwfDigitalInBufferSizeGet", handle, byref(before))
    if maximum.value <= 0:
        raise ValueError("AD2 reported an invalid DigitalIn buffer size")
    checked(dwf, "FDwfDigitalInBufferSizeSet", handle, c_int(maximum.value))
    # AutoConfigure is off: apply all pending DigitalIn settings while stopped,
    # before trusting Get values or starting the time-sensitive Record reader.
    checked(dwf, "FDwfDigitalInConfigure", handle, c_int(1), c_int(0))
    checked(dwf, "FDwfDigitalInBufferSizeGet", handle, byref(actual))
    report.update({"device_buffer_before_samples": before.value,
                   "device_buffer_max_samples": maximum.value,
                   "device_buffer_samples": actual.value,
                   "device_buffer_seconds": actual.value / rate})
    if actual.value != maximum.value:
        raise ValueError("AD2 did not apply the maximum DigitalIn buffer size")
    return actual.value


class DigitalRecordReader:
    """Drain the AD2 on one thread; disk, UART decoding and printing stay outside.

    This thread owns DigitalIn calls until it has joined. A bounded queue
    preserves sample order; a full queue or any SDK loss/corruption aborts.
    """
    def __init__(self, dwf, handle, buffer_size, queue_chunks=128):
        self.dwf, self.handle = dwf, handle
        self.buffer = (c_ubyte * buffer_size)()
        self.queue = Queue(maxsize=queue_chunks)
        self.stop = Event()
        self.finished = Event()
        self.error = None
        self.stats = {"lost_samples": 0, "corrupt_samples": 0,
                      "sampler_read_chunks": 0, "sampler_read_samples": 0,
                      "sampler_queue_high_water_chunks": 0,
                      "sampler_max_poll_gap_seconds": 0.0,
                      "sampler_max_read_seconds": 0.0,
                      "sampler_host_queue_overflow": False}
        self.thread = Thread(target=self._run, name="ad2-record-reader")

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.thread.join()

    def raise_if_failed(self):
        if self.error is not None:
            raise RuntimeError(str(self.error))

    def read(self, timeout=0.001):
        self.raise_if_failed()
        try:
            chunk = self.queue.get(timeout=timeout)
        except Empty:
            self.raise_if_failed()
            return None
        self.raise_if_failed()
        return chunk

    def _run(self):
        try:
            checked(self.dwf, "FDwfDigitalInConfigure", self.handle, c_int(0), c_int(1))
            previous_poll = time.monotonic()
            state, available, lost, corrupt = c_ubyte(), c_int(), c_int(), c_int()
            while not self.stop.is_set():
                now = time.monotonic()
                self.stats["sampler_max_poll_gap_seconds"] = max(
                    self.stats["sampler_max_poll_gap_seconds"], now - previous_poll)
                previous_poll = now
                checked(self.dwf, "FDwfDigitalInStatus", self.handle, c_int(1), byref(state))
                checked(self.dwf, "FDwfDigitalInStatusRecord", self.handle,
                        byref(available), byref(lost), byref(corrupt))
                self.stats["lost_samples"] += lost.value
                self.stats["corrupt_samples"] += corrupt.value
                self.stats["sampler_max_read_seconds"] = max(
                    self.stats["sampler_max_read_seconds"], time.monotonic() - now)
                if lost.value or corrupt.value:
                    self.stats["sampler_fault_after_samples"] = self.stats["sampler_read_samples"]
                    raise ValueError(f"AD2 sample loss/corruption; run invalid "
                                     f"(lost={lost.value}, corrupt={corrupt.value})")
                if available.value:
                    if available.value > len(self.buffer):
                        self.buffer = (c_ubyte * available.value)()
                    checked(self.dwf, "FDwfDigitalInStatusData2", self.handle,
                            self.buffer, c_int(0), c_int(available.value))
                    # Copy only valid samples in C; never enqueue a reusable ctypes view.
                    chunk = string_at(self.buffer, available.value)
                    self.stats["sampler_read_chunks"] += 1
                    self.stats["sampler_read_samples"] += len(chunk)
                    try:
                        self.queue.put_nowait(chunk)
                    except Full:
                        self.stats["sampler_host_queue_overflow"] = True
                        raise ValueError("AD2 host processing queue full; run invalid")
                    self.stats["sampler_queue_high_water_chunks"] = max(
                        self.stats["sampler_queue_high_water_chunks"], self.queue.qsize())
                self.stats["sampler_max_read_seconds"] = max(
                    self.stats["sampler_max_read_seconds"], time.monotonic() - now)
                # Keep draining immediately when data is available. Only yield
                # briefly when empty; Event.wait also makes shutdown prompt.
                if not available.value:
                    self.stop.wait(0.0005)
        except Exception as exc:
            self.error = exc
        finally:
            try:
                checked(self.dwf, "FDwfDigitalInConfigure", self.handle, c_int(0), c_int(0))
            except Exception as exc:
                if self.error is None:
                    self.error = exc
            self.finished.set()


def record(a):
    if not a.confirm_source_inactive or not a.confirm_txd_disconnected:
        raise ValueError("confirm GPS inactive until READY and CP2102 TXD disconnected")
    if not 1 <= a.tx_dio <= 7:
        raise ValueError("tx-dio must be in DIO1..DIO7; DIO0 is reserved for GPS reference")
    if a.baud <= 0 or not 16 * a.baud <= a.rate <= 2000000 or not math.isfinite(a.timeout) or a.timeout <= 0:
        raise ValueError("rate must provide 16 samples/bit and be at most 2000000 Hz; timeout positive")
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
              "baud": a.baud, "expected_bytes": context["bytes"], "requested_sample_rate_hz": a.rate,
              "lost_samples": 0, "corrupt_samples": 0, "ready_idle_verified": False, "invalid_reasons": [],
              "tx_dio": a.tx_dio,
              "note": f"AD2 input-only Record, DIO0=reference, DIO{a.tx_dio}=output. No search/byte trimming for alignment."}
    # Once hardware acquisition might begin, consume even on abort/failure.
    report["claim"] = claim_capture(context, a.registry)
    dwf, handle = None, c_int()
    reader = None
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
            _configure(fd, a.baud)
            dwf = CDLL("libdwf.so")
            devices = c_int()
            checked(dwf, "FDwfEnum", c_int(0), byref(devices))
            if not 0 <= a.device_index < devices.value:
                raise ValueError("AD2 device index not available")
            device, revision = c_int(), c_int()
            checked(dwf, "FDwfEnumDeviceType", c_int(a.device_index), byref(device), byref(revision))
            if device.value != 3:
                raise ValueError("selected instrument is not Analog Discovery 2")
            open_record_device(dwf, a.device_index, handle, report)
            checked(dwf, "FDwfDeviceAutoConfigureSet", handle, c_int(0))
            for i in range(16):
                checked(dwf, "FDwfDigitalOutEnableSet", handle, c_int(i), c_int(0))
            checked(dwf, "FDwfDigitalOutConfigure", handle, c_int(0))
            checked(dwf, "FDwfDigitalIOOutputEnableSet", handle, c_int(0))
            checked(dwf, "FDwfDigitalIOConfigure", handle)
            # Independent, instantaneous read through DigitalIO. This helps
            # distinguish a wiring/input-state issue from DigitalIn sample
            # packing or acquisition behavior during the P14 preflight.
            checked(dwf, "FDwfDigitalIOStatus", handle)
            dio_inputs = c_uint()
            checked(dwf, "FDwfDigitalIOInputStatus", handle, byref(dio_inputs))
            report["dio_static_input_mask"] = f"0x{dio_inputs.value:04X}"
            report["dio_static_input_levels"] = {
                f"DIO{i}": (dio_inputs.value >> i) & 1 for i in range(16)
            }
            hz = c_double()
            checked(dwf, "FDwfDigitalInInternalClockInfo", handle, byref(hz))
            divider = sample_divider(hz.value, a.rate, baud=a.baud)
            checked(dwf, "FDwfDigitalInDividerSet", handle, c_uint(divider))
            checked(dwf, "FDwfDigitalInAcquisitionModeSet", handle, c_int(3))
            checked(dwf, "FDwfDigitalInSampleFormatSet", handle, c_int(8))
            checked(dwf, "FDwfDigitalInTriggerSourceSet", handle, c_ubyte(0))
            checked(dwf, "FDwfDigitalInTriggerPositionSet", handle, c_int(0))
            buffer_size = configure_record_buffer(dwf, handle, hz.value / divider, report)
            applied_divider = c_uint()
            checked(dwf, "FDwfDigitalInDividerGet", handle, byref(applied_divider))
            report["requested_sampling_divider"] = divider
            report["sampling_divider"] = applied_divider.value
            if applied_divider.value != divider:
                raise ValueError(f"AD2 did not apply sampling divider: requested={divider}, "
                                 f"actual={applied_divider.value}; acquisition not started")
            rate = hz.value / applied_divider.value
            report["sample_rate_hz"] = rate
            report["sample_format"] = f"unsigned 8-bit, DIO0 bit0 / DIO{a.tx_dio} bit{a.tx_dio}"
            decoders = [UARTDecoder(rate, baud=a.baud, bit=i, limit=context["bytes"])
                        for i in (0, a.tx_dio)]
            preflight = CommonIdlePreflight(rate, a.baud, a.tx_dio, report)
            for decoder in decoders:
                # Keep frame timestamps absolute within the unmodified raw file.
                decoder.offset = preflight.warmup_limit
            print(f"ARMING: AD2 {rate:.0f} samples/s, buffer={buffer_size} samples; "
                  "20 ms stabilization + 250 ms idle; keep GPS inactive until READY", flush=True)
            reader = stack.enter_context(DigitalRecordReader(dwf, handle, buffer_size))
            report["sampler"] = "dedicated DigitalIn reader; bounded FIFO queue; no sample dropping"
            ready_at = None
            started = time.monotonic()
            while time.monotonic() - started < a.timeout:
                chunk = reader.read()
                if chunk:
                    raw.write(chunk)
                    samples_total += len(chunk)
                    if ready_at is None:
                        chunk = preflight.feed(chunk)
                    for decoder in decoders:
                        decoder.feed(chunk)
                if select.select([fd], [], [], 0)[0]:
                    data = os.read(fd, 4096)
                    if ready_at is None and data:
                        raise ValueError("CP2102 received bytes before READY")
                    serial.extend(data[:max(0, context["bytes"] - len(serial))])
                if ready_at is None and preflight.ready:
                    ready_at = time.monotonic()
                    report["ready_idle_verified"] = True
                    report["ready_sample_offset"] = samples_total
                    print("READY: AD2 + CP2102 armed; enable GPS now. Do not press KEY0.", flush=True)
                if ready_at is not None and all(len(d.data) == context["bytes"] for d in decoders) and len(serial) == context["bytes"]:
                    report["status"] = "CAPTURED"
                    break
            if report["status"] != "CAPTURED":
                report["invalid_reasons"].append("timeout/incomplete capture")
                report["status"] = "FAIL"
    except (OSError, termios.error, ValueError, RuntimeError, KeyboardInterrupt) as exc:
        report["invalid_reasons"].append(str(exc) or "interrupted")
        report["status"] = "FAIL"
    finally:
        if reader is not None:
            report.update(reader.stats)
            if reader.error is not None:
                reason = str(reader.error)
                if reason not in report["invalid_reasons"]:
                    report["invalid_reasons"].append(reason)
                report["status"] = "FAIL"
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
    if report["status"] == "PASS":
        try:
            report["physical_uart_metrics"] = frame_metrics(acquisition, context["bytes"])
        except ValueError as exc:
            # Byte evidence remains valid; missing timestamps never fabricate timing.
            report["physical_uart_metrics"] = {"status": "UNAVAILABLE", "reason": str(exc)}
    rate = acquisition.get("sample_rate_hz")
    report["physical_latency_note"] = (
        f"{1e6 / rate:g}-us digital sample period; not AES core latency"
        if isinstance(rate, (int, float)) and math.isfinite(rate) and rate > 0
        else "Actual digital sample period unavailable; no physical timing claim")
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
    r.add_argument("--baud", type=int, default=9600)
    r.add_argument("--timeout", type=float, default=90)
    r.add_argument("--device-index", type=int, default=0)
    r.add_argument("--tx-dio", type=int, default=1,
                   help="AD2 DIO line observing FPGA TX (DIO1..DIO7; DIO0 is the GPS reference)")
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
