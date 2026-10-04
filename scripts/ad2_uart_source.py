#!/usr/bin/env python3
"""Drive DE10-Lite UART RX from AD2 DIO0, read echo via CP2102 RXD.

Diagnostic only. Disconnect CP2102 TXD from FPGA RX before using DIO0.
WaveForms GUI must be closed while the SDK owns the AD2.
"""

import argparse
from ctypes import CDLL, byref, c_double, c_int, c_ubyte, create_string_buffer
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import serial


def checked(dwf, name, *args):
    if getattr(dwf, name)(*args) == 0:
        error = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(error)
        raise RuntimeError(f"{name}: {error.value.decode(errors='replace')}")


def run(port, payload, timeout, baud=9600, capture_scope=False):
    dwf = CDLL("libdwf.so")
    handle = c_int()
    checked(dwf, "FDwfDeviceOpen", c_int(-1), byref(handle))
    if handle.value == 0:
        raise RuntimeError("AD2 did not open")
    try:
        checked(dwf, "FDwfDigitalUartRateSet", handle, c_double(baud))
        checked(dwf, "FDwfDigitalUartTxSet", handle, c_int(0))  # DIO0
        checked(dwf, "FDwfDigitalUartBitsSet", handle, c_int(8))
        checked(dwf, "FDwfDigitalUartParitySet", handle, c_int(0))
        checked(dwf, "FDwfDigitalUartStopSet", handle, c_double(1))
        checked(dwf, "FDwfDigitalUartTx", handle, None, c_int(0))  # idle high
        scope = None
        if capture_scope:
            samples = 8192
            sample_hz = 250000
            checked(dwf, "FDwfDeviceAutoConfigureSet", handle, c_int(0))
            checked(dwf, "FDwfAnalogInFrequencySet", handle, c_double(sample_hz))
            checked(dwf, "FDwfAnalogInBufferSizeSet", handle, c_int(samples))
            checked(dwf, "FDwfAnalogInChannelEnableSet", handle, c_int(-1), c_int(1))
            # AD2 at the 5 V range clipped this 3.3 V signal to ~2.77 V.
            checked(dwf, "FDwfAnalogInChannelRangeSet", handle, c_int(-1), c_double(10))
            checked(dwf, "FDwfAnalogInTriggerSourceSet", handle, c_ubyte(0))
            checked(dwf, "FDwfAnalogInConfigure", handle, c_int(1), c_int(0))
            time.sleep(0.5)
        with serial.Serial(port, baudrate=baud, bytesize=8,
                           parity="N", stopbits=1, timeout=0.05,
                           write_timeout=1) as receiver:
            receiver.reset_input_buffer()
            time.sleep(0.1)
            stimulus = create_string_buffer(payload)
            if capture_scope:
                checked(dwf, "FDwfAnalogInConfigure", handle, c_int(0), c_int(1))
            started = time.monotonic()
            checked(dwf, "FDwfDigitalUartTx", handle, stimulus, c_int(len(payload)))
            received = bytearray()
            deadline = started + timeout
            while len(received) < len(payload) and time.monotonic() < deadline:
                received.extend(receiver.read(len(payload) - len(received)))
            time.sleep(0.02)  # allow any unexpected extra bytes to arrive
            extra = receiver.read(receiver.in_waiting) if receiver.in_waiting else b""
            elapsed = time.monotonic() - started
        if capture_scope:
            status = c_ubyte()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                checked(dwf, "FDwfAnalogInStatus", handle, c_int(1), byref(status))
                if status.value == 2:  # DwfStateDone
                    break
                time.sleep(0.01)
            else:
                raise TimeoutError("AD2 scope acquisition did not finish")
            first = (c_double * samples)()
            second = (c_double * samples)()
            checked(dwf, "FDwfAnalogInStatusData", handle, c_int(0), first, c_int(samples))
            checked(dwf, "FDwfAnalogInStatusData", handle, c_int(1), second, c_int(samples))
            scope = (sample_hz, list(first), list(second))
        return bytes(received), extra, elapsed, scope
    finally:
        dwf.FDwfDeviceClose(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--design", required=True, choices=("wire_diag", "baseline"),
                        help="bitstream actually programmed on the FPGA")
    parser.add_argument("--hex", default="55 A5 00 FF 3C")
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--baud", type=int, default=9600,
                        help="UART baud rate (default: 9600)")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--scope-csv", type=Path,
                        help="save CH1=V10 and CH2=W10 analog samples to a new CSV")
    parser.add_argument("--confirm-txd-disconnected", action="store_true",
                        help="confirm CP2102 TXD is physically disconnected from FPGA RX")
    args = parser.parse_args()
    if not args.confirm_txd_disconnected:
        parser.error("remove CP2102 TXD -> FPGA RX, then pass --confirm-txd-disconnected")
    try:
        payload = bytes.fromhex(args.hex)
    except ValueError as exc:
        parser.error(f"invalid hex payload: {exc}")
    if not payload or args.timeout <= 0:
        parser.error("payload and timeout must be positive")
    if args.baud <= 0:
        parser.error("baud must be positive")
    received, extra, elapsed, scope = run(args.port, payload, args.timeout,
                                          baud=args.baud,
                                          capture_scope=bool(args.scope_csv))
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "test": "AD2 DIO0 -> FPGA RX -> FPGA TX -> CP2102 RXD",
        "format": f"{args.baud}/8N1",
        "port": args.port,
        "design": args.design,
        "sent_hex": payload.hex(" ").upper(),
        "received_hex": received.hex(" ").upper(),
        "extra_hex": extra.hex(" ").upper(),
        "elapsed_seconds": elapsed,
        "status": "PASS" if received == payload and not extra else "FAIL",
    }
    if scope:
        sample_hz, first, second = scope
        report["scope"] = {
            "csv": str(args.scope_csv),
            "sample_hz": sample_hz,
            "samples": len(first),
            "ch1_v10_min_v": min(first),
            "ch1_v10_max_v": max(first),
            "ch1_v10_samples_below_1_5_v": sum(v < 1.5 for v in first),
            "ch2_w10_min_v": min(second),
            "ch2_w10_max_v": max(second),
            "ch2_w10_samples_below_1_5_v": sum(v < 1.5 for v in second),
        }
        args.scope_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.scope_csv.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("time_s", "ch1_v10_v", "ch2_w10_v"))
            writer.writerows((index / sample_hz, first[index], second[index])
                             for index in range(len(first)))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, serial.SerialException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
