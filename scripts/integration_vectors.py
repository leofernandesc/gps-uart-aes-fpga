#!/usr/bin/env python3
"""Public fixtures and independent checking of bytes decoded from UART TX."""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import cryptography
from cryptography.hazmat.backends.openssl.backend import backend

from ctr_vectors import crypt, deterministic_bytes
from capture import compare
from gps_fixture import load_replay

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/integration"


def cases():
    nmea_replay = load_replay()
    payloads = [bytes([0x55]), bytes(range(15)), bytes(range(16)), bytes(range(17)),
                nmea_replay, bytes(range(255)), bytes(i % 256 for i in range(2049)),
                bytes(range(16)), b"\x00\xff\x55"]
    result = []
    for index, plain in enumerate(payloads):
        label = f"uart-integration-{index}"
        key, nonce = deterministic_bytes(label + "key", 16), deterministic_bytes(label + "nonce", 12)
        counter = 0xffffffff if index == 7 else 0xff + index
        result.append((key, nonce, counter, plain, crypt(key, nonce, counter, plain)))
    return result


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    records = cases()
    lines = [str(len(records))]
    for key, nonce, counter, plain, encrypted in records:
        lines.append(f"{key.hex()} {nonce.hex()} {counter:08x} {len(plain)}")
        lines.extend(f"{a:02x} {b:02x}" for a, b in zip(plain, encrypted))
    (OUT / "vectors.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"PASS integration fixtures: {len(records)} public synthetic streams")


def verify():
    report = {"kind": "RTL simulation, not physical capture", "runs": {},
              "python": platform.python_version(), "cryptography": cryptography.__version__,
              "openssl": backend.openssl_version_text()}
    for mode in ("baseline", "secure"):
        for speed in ("fast", "50mhz"):
            name = f"{mode}-{speed}"
            path = OUT / f"{name}.txt"
            lines = iter(path.read_text(encoding="ascii").splitlines())
            records = cases() if speed == "fast" else cases()[:4]
            total, recovered_hash = 0, hashlib.sha256()
            for case_id, (key, nonce, counter, plain, encrypted) in enumerate(records):
                actual = bytearray()
                for offset in range(len(plain)):
                    row = next(lines, "").split()
                    if len(row) != 3 or row[:2] != [str(case_id), str(offset)]:
                        raise ValueError(f"{name}: truncated/reordered output at {case_id}:{offset}")
                    actual.append(int(row[2], 16))
                expected = encrypted if mode == "secure" else plain
                context = {"mode": "aes-128-ctr" if mode == "secure" else "baseline",
                           "bytes": len(plain), "key_hex": key.hex(), "nonce_hex": nonce.hex(),
                           "initial_counter": counter}
                comparison, recovered = compare(plain, actual, context)
                if actual != expected or recovered != plain or comparison["status"] != "PASS":
                    raise ValueError(f"{name}: byte mismatch in case {case_id}")
                recovered_hash.update(recovered)
                total += len(actual)
            if next(lines, None) is not None:
                raise ValueError(f"{name}: unexpected trailing bytes")
            report["runs"][name] = {
                "status": "PASS", "streams": len(records), "bytes": total,
                "serial_output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "recovered_sha256": recovered_hash.hexdigest(),
            }
            print(f"PASS PC serial verification: {name}, {len(records)} streams, {total} bytes")
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    verify() if args.verify else generate()
