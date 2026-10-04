#!/usr/bin/env python3
"""Export one approved, consumed test context; never export the nonce registry."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from ad2_live_capture import assess
from build_manifest import ROOT, digest
from context import validate_context
from live_timing import frame_metrics


def export(capture, context_file, registry_file, output, authorized=False):
    if not authorized:
        raise ValueError("explicit permission to publish real GPS coordinates and test key required")
    output = output.resolve()
    if not output.is_relative_to(ROOT / "reference/experiments"):
        raise ValueError("public output must be a new directory below reference/experiments")
    context = json.loads(context_file.read_text())
    validate_context(context)
    acquisition = json.loads((capture / "acquisition.json").read_text())
    previous = json.loads((capture / "comparison.json").read_text())
    if context["mode"] != "aes-128-ctr":
        raise ValueError("export expects a selected AES-CTR test context")
    registry = json.loads(registry_file.read_text())
    matches = [r for r in registry["contexts"] if r["context_id"] == context["context_id"]]
    if len(matches) != 1 or not matches[0].get("capture_started_utc"):
        raise ValueError("test context not consumed; never publish a future session key")
    if acquisition["context_sha256"] != digest(context_file):
        raise ValueError("context/acquisition mismatch")
    if previous.get("acquisition_sha256") != digest(capture / "acquisition.json"):
        raise ValueError("comparison/acquisition mismatch")
    for name, expected in acquisition["artifacts_sha256"].items():
        if Path(name).name != name or digest(capture / name) != expected:
            raise ValueError("modified/unsafe acquired artifact")
    result, recovered = assess(*[(capture / name).read_bytes() for name in
        ("reference.bin", "cipher.bin", "cp2102.bin")], context, acquisition)
    observations = previous.get("operator_observations", {})
    if result["status"] != "PASS" or previous.get("status") != "PASS" or not all(
            observations.get(n) is True for n in ("overflow_off", "framing_off", "no_reset")):
        raise ValueError("selected trial not approved")
    if recovered != (capture / "recovered.bin").read_bytes():
        raise ValueError("stored recovery differs from independent decryption")
    # Whitelist: no private paths, other keys, or registry contents exported.
    public_context = {k: context[k] for k in ("schema", "context_id", "mode", "bytes",
                                            "key_hex", "nonce_hex", "initial_counter", "key_sha256")}
    public_context.update(counter_byte_order="big-endian", purpose="PUBLIC CONSUMED TEST KEY ONLY")
    output.mkdir(parents=True, exist_ok=False)
    for name in ("reference.bin", "cipher.bin", "cp2102.bin", "recovered.bin"):
        shutil.copyfile(capture / name, output / name)
    (output / "test-context.json").write_text(json.dumps(public_context, indent=2) + "\n")
    result["operator_observations"] = observations
    result["physical_uart_metrics"] = frame_metrics(acquisition, context["bytes"])
    result["source_comparison_sha256"] = digest(capture / "comparison.json")
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    timing = {k: acquisition[k] for k in ("sample_rate_hz", "baud", "reference_frame_start_samples",
                                         "cipher_frame_start_samples", "sof_sha256")}
    (output / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
    (output / "README.md").write_text(
        "# Public P18 live-GPS test artifact\n\n"
        "This explicitly authorized copy contains real coordinates and a consumed dedicated test key. "
        "Never reuse this key/nonce for an independent operational stream. No nonce registry is published.\n\n"
        "From the repository root:\n\n"
        "```bash\npython3 scripts/publish_experiment.py verify --input " +
        str(output.relative_to(ROOT)) + "\n```\n\n"
        "The verification decrypts with an independent Python library, checks every byte and validates "
        "NMEA checksums. Nonce: 96 bits; counter: 32-bit big-endian; initial value in test-context.json. "
        "This 1,024-byte pilot is not the planned long campaign.\n")
    manifest = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / "sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {"status": "EXPORTED", "output": str(output), "files": len(manifest),
            "note": "Only selected public test data exported; private originals unchanged."}


def check_export(directory):
    from ctr_vectors import crypt
    from gps_fixture import parse_window
    hashes = json.loads((directory / "sha256.json").read_text())
    for name, expected in hashes.items():
        if Path(name).name != name or digest(directory / name) != expected:
            raise ValueError("public artifact modified/unsafe path")
    context = json.loads((directory / "test-context.json").read_text())
    validate_context(context)
    reference = (directory / "reference.bin").read_bytes()
    cipher = (directory / "cipher.bin").read_bytes()
    recovered = crypt(bytes.fromhex(context["key_hex"]), bytes.fromhex(context["nonce_hex"]),
                      context["initial_counter"], cipher)
    if len(reference) != context["bytes"] or reference != recovered or recovered != (
            directory / "recovered.bin").read_bytes() or cipher != (directory / "cp2102.bin").read_bytes():
        raise ValueError("public byte-exact verification failed")
    sentences, _, _ = parse_window(reference)
    return {"status": "PASS", "bytes": len(reference), "nmea_sentences": len(sentences)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("export")
    for name in ("capture", "context", "registry", "output"):
        a.add_argument("--" + name, type=Path, required=True)
    a.add_argument("--ack-public-gps-and-test-key", action="store_true")
    a = sub.add_parser("verify")
    a.add_argument("--input", type=Path, required=True)
    args = p.parse_args()
    try:
        result = (export(args.capture, args.context, args.registry, args.output,
                         args.ack_public_gps_and_test_key) if args.action == "export"
                  else check_export(args.input))
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL public experiment: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
