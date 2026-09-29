#!/usr/bin/env python3
"""Static AD2 DIO0 -> FPGA V10 -> FPGA W10 continuity probe.

Only run with wire_diag SOF and CP2102 TXD disconnected from V10.
CH1+ must be on the selected --ch1-point, CH2+ on W10; negatives on common GND.
"""

import argparse
from ctypes import CDLL, byref, c_double, c_int, create_string_buffer
from datetime import datetime, timezone
import json
from pathlib import Path
import time


def checked(dwf, name, *args):
    if getattr(dwf, name)(*args) == 0:
        error = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(error)
        raise RuntimeError(f"{name}: {error.value.decode(errors='replace')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-txd-disconnected", action="store_true")
    parser.add_argument("--ch1-point", required=True, choices=("V10", "DIO0"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.confirm_txd_disconnected:
        parser.error("disconnect CP2102 TXD from V10 before driving AD2 DIO0")

    dwf = CDLL("libdwf.so")
    handle = c_int()
    checked(dwf, "FDwfDeviceOpen", c_int(-1), byref(handle))
    if not handle.value:
        raise RuntimeError("AD2 did not open")
    try:
        checked(dwf, "FDwfDeviceAutoConfigureSet", handle, c_int(0))
        checked(dwf, "FDwfAnalogInChannelEnableSet", handle, c_int(-1), c_int(1))
        checked(dwf, "FDwfAnalogInChannelRangeSet", handle, c_int(-1), c_double(10))
        checked(dwf, "FDwfAnalogInConfigure", handle, c_int(0), c_int(0))
        time.sleep(0.5)
        checked(dwf, "FDwfDigitalIOOutputEnableSet", handle, c_int(1))
        readings = []
        for level in (1, 0, 1):
            checked(dwf, "FDwfDigitalIOOutputSet", handle, c_int(level))
            checked(dwf, "FDwfDigitalIOConfigure", handle)
            time.sleep(0.2)
            checked(dwf, "FDwfDigitalIOStatus", handle)
            digital = c_int()
            checked(dwf, "FDwfDigitalIOInputStatus", handle, byref(digital))
            checked(dwf, "FDwfAnalogInStatus", handle, c_int(0), None)
            ch1 = c_double()
            ch2 = c_double()
            checked(dwf, "FDwfAnalogInStatusSample", handle, c_int(0), byref(ch1))
            checked(dwf, "FDwfAnalogInStatusSample", handle, c_int(1), byref(ch2))
            readings.append({"dio0_command": level,
                             "dio0_readback": digital.value & 1,
                             "ch1_v": ch1.value,
                             "ch2_w10_v": ch2.value})
        report = {"created_utc": datetime.now(timezone.utc).isoformat(),
                  "ch1_point": args.ch1_point, "ch2_point": "W10",
                  "measurements": readings}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2)
                stream.write("\n")
        print(json.dumps(report, indent=2))
    finally:
        dwf.FDwfDigitalIOOutputEnableSet(handle, c_int(0))
        dwf.FDwfDigitalIOConfigure(handle)
        dwf.FDwfDeviceClose(handle)


if __name__ == "__main__":
    main()
