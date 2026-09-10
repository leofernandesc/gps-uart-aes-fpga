#!/usr/bin/env python3
"""Independent CTR test fixtures and verification of actual RTL output.

All keys/nonces here are public deterministic test data. Production session
provisioning and persistent nonce allocation belong to the later PC software.
No RTL source or internal signal is used to calculate expected results.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

import cryptography
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/ctr"
REFERENCE = ROOT / "reference/ctr-sp800-38a/aes128.json"


def crypt(key, nonce, initial_counter, payload):
    if len(key) != 16 or len(nonce) != 12:
        raise ValueError("Expected a 16-byte key and 12-byte nonce")
    if not 0 <= initial_counter <= 0xffffffff:
        raise ValueError("Counter outside 32-bit range")
    if (len(payload) + 15) // 16 > (1 << 32) - initial_counter:
        raise ValueError("Payload would wrap the 32-bit counter")
    ctx = Cipher(algorithms.AES(key), modes.CTR(
        nonce + initial_counter.to_bytes(4, "big"))).encryptor()
    return ctx.update(payload) + ctx.finalize()


def deterministic_bytes(label, size):
    return hashlib.shake_256(label.encode("ascii")).digest(size)


def cases():
    reference = json.loads(REFERENCE.read_text(encoding="ascii"))
    key = bytes.fromhex(reference["key"])
    counter_block = bytes.fromhex(reference["initial_counter_block"])
    nonce, counter = counter_block[:12], int.from_bytes(counter_block[12:], "big")
    plain, cipher = (bytes.fromhex(reference[k]) for k in ("plaintext", "ciphertext"))
    if crypt(key, nonce, counter, plain) != cipher or crypt(key, nonce, counter, cipher) != plain:
        raise RuntimeError("Independent library disagrees with SP 800-38A F.5.1/F.5.2")

    streams = [("nist_encrypt", key, nonce, counter, plain, cipher, 0),
               ("nist_decrypt", key, nonce, counter, cipher, plain, 1)]
    lengths = (1, 2, 7, 15, 16, 17, 31, 32, 33, 63, 64, 65, 255, 256, 257, 1024, 4097)
    for length in lengths:
        for schedule in range(3):
            label = f"synthetic-{length}-{schedule}"
            test_key = deterministic_bytes(label + "key", 16)
            test_nonce = deterministic_bytes(label + "nonce", 12)
            start = (0, 0xfe, 0xfffe)[schedule]
            data = deterministic_bytes(label + "bytes", length)
            streams.append(("synthetic", test_key, test_nonce, start, data,
                            crypt(test_key, test_nonce, start, data), schedule))
    for start, length in ((0xffffffff, 1), (0xffffffff, 15), (0xffffffff, 16),
                          (0xfffffffe, 17), (0xfffffffe, 31), (0xfffffffe, 32),
                          (0xfffffffc, 64)):
        label = f"boundary-{start}-{length}"
        test_nonce = deterministic_bytes(label, 12)
        data = deterministic_bytes(label, length)
        streams.append(("counter_boundary", key, test_nonce, start, data,
                        crypt(key, test_nonce, start, data), 1))

    masks = [(key, nonce, counter, 4)]
    for n in range(32):
        masks.append((deterministic_bytes(f"mask-key-{n}", 16),
                      deterministic_bytes(f"mask-nonce-{n}", 12),
                      (0, 0xfe, 0xfffe, 0xfffffffd)[n % 4], (n % 3) + 1))
    masks.extend((key, nonce, start, count) for start, count in
                 ((0xffffffff, 1), (0xfffffffe, 2), (0xfffffffd, 3)))

    for start, length in ((0xffffffff, 17), (0xfffffffe, 33), (0xfffffffc, 65)):
        try:
            crypt(key, nonce, start, bytes(length))
        except ValueError:
            pass
        else:
            raise RuntimeError("Oracle accepted counter wrap")
    return streams, masks


def generate(streams, masks):
    OUT.mkdir(parents=True, exist_ok=True)
    stream_lines = [str(len(streams))]
    for _, key, nonce, start, source, expected, schedule in streams:
        terminal = int(len(source) == ((1 << 32) - start) * 16)
        stream_lines.append(f"{key.hex()} {nonce.hex()} {start:08x} {len(source)} {schedule} {terminal}")
        stream_lines.extend(f"{a:02x} {b:02x}" for a, b in zip(source, expected))
    mask_lines = [str(len(masks))]
    for key, nonce, start, count in masks:
        mask_lines.append(f"{key.hex()} {nonce.hex()} {start:08x} {count}")
        output = crypt(key, nonce, start, bytes(16 * count))
        mask_lines.extend(f"{output[i * 16:(i + 1) * 16].hex()} {int(start + i == 0xffffffff)}"
                          for i in range(count))
    payloads = {"stream-vectors.txt": "\n".join(stream_lines) + "\n",
                "mask-vectors.txt": "\n".join(mask_lines) + "\n"}
    for filename, payload in payloads.items():
        (OUT / filename).write_text(payload, encoding="ascii")
    metadata = {"stream_cases": len(streams), "stream_bytes": sum(len(c[4]) for c in streams),
                "groups": dict(Counter(c[0] for c in streams)), "mask_sessions": len(masks),
                "mask_blocks": sum(c[3] for c in masks), "python": platform.python_version(),
                "cryptography": cryptography.__version__, "openssl": backend.openssl_version_text(),
                "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                "files": {name: hashlib.sha256(data.encode("ascii")).hexdigest()
                          for name, data in payloads.items()}}
    (OUT / "oracle.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"PASS CTR oracle: {len(streams)} streams, {metadata['stream_bytes']} bytes; "
          f"{len(masks)} mask sessions; NIST encrypt/decrypt + synthetic + counter boundary")


def verify(streams):
    path = OUT / "rtl-bytes.txt"
    lines = iter(path.read_text(encoding="ascii").splitlines())
    total = 0
    for case_id, (_, key, nonce, start, source, expected, _) in enumerate(streams):
        actual = bytearray()
        for offset in range(len(source)):
            try:
                row = next(lines).split()
            except StopIteration as exc:
                raise RuntimeError(f"RTL output truncated at case {case_id}, byte {offset}") from exc
            if len(row) != 3 or [int(v) for v in row[:2]] != [case_id, offset]:
                raise RuntimeError(f"RTL output ordering mismatch at {case_id}:{offset}")
            actual.append(int(row[2], 16))
        if actual != expected or crypt(key, nonce, start, bytes(actual)) != source:
            raise RuntimeError(f"PC decrypt/byte comparison failed for case {case_id}")
        total += len(actual)
    if next(lines, None) is not None:
        raise RuntimeError("Unexpected trailing RTL bytes")
    result = {"status": "PASS", "cases": len(streams), "bytes": total,
              "rtl_output_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT / "pc-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(f"PASS PC verification: {len(streams)} RTL streams, {total} bytes, independent CTR recovery")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify actual RTL bytes after simulation")
    arguments = parser.parse_args()
    stream_cases, mask_cases = cases()
    if arguments.verify:
        verify(stream_cases)
    else:
        generate(stream_cases, mask_cases)
