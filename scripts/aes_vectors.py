#!/usr/bin/env python3
"""Independent AES oracle: public NIST cases + deterministic synthetic inputs.

Run on the host before the HDL container; never imports or parses the DUT RTL.
Only writes generated, public test data under the project's build/aes directory.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

import cryptography
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference/aes-cavp"
OUT = ROOT / "build/aes"


def encrypt(key, plaintext):
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update(plaintext) + enc.finalize()


def cavp_cases(path):
    enabled = False
    record = {}
    for line in path.read_text(encoding="ascii").splitlines():
        line = line.strip()
        if line.startswith("["):
            enabled = line == "[ENCRYPT]"
            record = {}
        elif enabled and " = " in line:
            field, value = line.split(" = ", 1)
            record[field] = value
            if field == "CIPHERTEXT":
                yield tuple(bytes.fromhex(record[k]) for k in ("KEY", "PLAINTEXT", "CIPHERTEXT"))
                record = {}


def main():
    for line in (REF / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        expected_hash, filename = line.split()
        if hashlib.sha256((REF / filename).read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError(f"Changed NIST reference: {filename}")

    cases = []
    counts = Counter()

    def add(label, key, plaintext, expected=None):
        if len(key) != 16 or len(plaintext) != 16:
            raise ValueError("AES-128 requires 16-byte keys and blocks")
        actual = encrypt(key, plaintext)
        if expected is not None and actual != expected:
            raise RuntimeError(f"Independent library disagrees with {label}")
        cases.append((key, plaintext, actual))
        counts[label] += 1

    for filename, expected_count in (("ECBGFSbox128.rsp", 7), ("ECBKeySbox128.rsp", 21),
                                     ("ECBVarKey128.rsp", 128), ("ECBVarTxt128.rsp", 128)):
        for key, plaintext, expected in cavp_cases(REF / filename):
            add(filename, key, plaintext, expected)
        if counts[filename] != expected_count:
            raise RuntimeError(f"Unexpected ENCRYPT case count for {filename}")

    # FIPS 197 cipher examples, plus SP 800-38A F.1.1 / NIST AES_Core128.pdf.
    examples = [
        ("000102030405060708090a0b0c0d0e0f", "00112233445566778899aabbccddeeff", "69c4e0d86a7b0430d8cdb78070b4c55a"),
        ("2b7e151628aed2a6abf7158809cf4f3c", "3243f6a8885a308d313198a2e0370734", "3925841d02dc09fbdc118597196a0b32"),
        ("2b7e151628aed2a6abf7158809cf4f3c", "6bc1bee22e409f96e93d7e117393172a", "3ad77bb40d7a3660a89ecaf32466ef97"),
        ("2b7e151628aed2a6abf7158809cf4f3c", "ae2d8a571e03ac9c9eb76fac45af8e51", "f5d3d58503b9699de785895a96fdbaaf"),
        ("2b7e151628aed2a6abf7158809cf4f3c", "30c81c46a35ce411e5fbc1191a0a52ef", "43b1cd7f598ece23881b00e3ed030688"),
        ("2b7e151628aed2a6abf7158809cf4f3c", "f69f2445df4f9b17ad2b417be66c3710", "7b0c785e27e8ad3f8223207104725dd4"),
    ]
    for key, plaintext, expected in examples:
        add("published_examples", bytes.fromhex(key), bytes.fromhex(plaintext), bytes.fromhex(expected))

    # SHA-256-derived bytes: deterministic test fixtures, never production keys.
    for n in range(512):
        digest = hashlib.sha256(f"gps-uart-aes-test-v1:{n}".encode("ascii")).digest()
        add("synthetic_changing_key", digest[:16], digest[16:])
    fixed_key = bytes.fromhex(examples[0][0])
    for n in range(64):
        plaintext = hashlib.sha256(f"gps-uart-aes-reuse-v1:{n}".encode("ascii")).digest()[:16]
        add("synthetic_reused_key", fixed_key, plaintext)

    OUT.mkdir(parents=True, exist_ok=True)
    payload = str(len(cases)) + "\n" + "".join(" ".join(v.hex() for v in row) + "\n" for row in cases)
    (OUT / "vectors.txt").write_text(payload, encoding="ascii")
    metadata = {"count": len(cases), "groups": dict(counts), "python": platform.python_version(),
                "cryptography": cryptography.__version__, "openssl": backend.openssl_version_text(),
                "vectors_sha256": hashlib.sha256(payload.encode("ascii")).hexdigest()}
    (OUT / "oracle.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"PASS AES oracle: {len(cases)} cases; 284 CAVP + 6 examples + 576 synthetic; independent cryptography/OpenSSL")


if __name__ == "__main__":
    main()
