#!/usr/bin/env python3
"""Read AD2 digital input levels without generating signals."""
import argparse
from ctypes import CDLL, byref, c_int, c_uint, create_string_buffer
import json
import time


def checked(dwf, name, *args):
    if getattr(dwf, name)(*args) == 0:
        message = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(message)
        raise RuntimeError(f"{name}: {message.value.decode(errors='replace')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval-ms", type=float, default=100)
    args = parser.parse_args()
    if args.device_index < 0 or not 1 <= args.samples <= 100 or args.interval_ms < 0:
        parser.error("device-index >= 0, samples 1..100, interval-ms >= 0")

    dwf = CDLL("libdwf.so")
    devices = c_int()
    checked(dwf, "FDwfEnum", c_int(0), byref(devices))
    if args.device_index >= devices.value:
        raise RuntimeError(f"AD2 index {args.device_index} unavailable; enumerated {devices.value} device(s)")

    handle = c_int()
    checked(dwf, "FDwfDeviceOpen", c_int(args.device_index), byref(handle))
    if not handle.value:
        raise RuntimeError("AD2 did not open; close WaveForms and retry")

    try:
        device_type, revision = c_int(), c_int()
        checked(dwf, "FDwfEnumDeviceType", c_int(args.device_index), byref(device_type), byref(revision))
        if device_type.value != 3:
            raise RuntimeError(f"device index {args.device_index} is type {device_type.value}, not AD2")

        # Put every digital line in high impedance; this utility never drives DIO.
        for channel in range(16):
            checked(dwf, "FDwfDigitalOutEnableSet", handle, c_int(channel), c_int(0))
        checked(dwf, "FDwfDigitalOutConfigure", handle, c_int(0))
        checked(dwf, "FDwfDigitalIOOutputEnableSet", handle, c_int(0))
        checked(dwf, "FDwfDigitalIOConfigure", handle)

        reads = []
        for index in range(args.samples):
            checked(dwf, "FDwfDigitalIOStatus", handle)
            mask = c_uint()
            checked(dwf, "FDwfDigitalIOInputStatus", handle, byref(mask))
            reads.append({
                "sample": index + 1,
                "mask": f"0x{mask.value:04X}",
                **{f"DIO{line}": (mask.value >> line) & 1 for line in range(16)},
            })
            if index + 1 < args.samples:
                time.sleep(args.interval_ms / 1000)
        print(json.dumps({"device": "AD2", "digital_outputs": "disabled/input-only", "reads": reads}, indent=2))
    finally:
        dwf.FDwfDeviceClose(handle)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as exc:
        raise SystemExit(f"ERROR: {exc}")
