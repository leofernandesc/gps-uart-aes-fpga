#!/usr/bin/env python3
"""Prepare a private, hash-bound 1 MiB UART replay runbook; never runs hardware."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

from build_manifest import ROOT, digest, verify
from capture import private_file
from context import validate_context


def command(*parts):
    return shlex.join(map(str, parts))


def prepare(fixture, fixture_report, baseline_context, secure_context,
            baseline_build, secure_build, registry, output,
            quartus_bin=None,
            port="/dev/ttyUSB0"):
    if quartus_bin is None:
        quartus_sh = shutil.which("quartus_sh")
        if not quartus_sh:
            raise ValueError("Quartus not found; set --quartus-bin or add quartus_sh to PATH")
        quartus_bin = Path(quartus_sh).resolve().parent
    output = output.resolve()
    if not output.is_relative_to(ROOT / "data/private"):
        raise ValueError("runbook must be below data/private")
    if output.exists():
        raise FileExistsError(f"runbook output already exists: {output}")
    paths = [fixture, fixture_report, baseline_context, secure_context]
    if any(not p.resolve().is_relative_to(ROOT / "data/private") for p in paths):
        raise ValueError("fixture, report, and contexts must remain private")
    metadata = json.loads(fixture_report.read_text())
    if digest(fixture) != metadata.get("sha256") or fixture.stat().st_size != 1048576:
        raise ValueError("fixture hash/size does not match its generation report")
    if metadata.get("source") != "Repeated stored GPS workload, NOT new live GPS acquisition":
        raise ValueError("fixture is not explicitly identified as stored-data replay")

    specs = []
    for mode, context_path, build_path, design in (
        ("baseline", baseline_context, baseline_build, "baseline"),
        ("aes-128-ctr", secure_context, secure_build, "secure"),
    ):
        context = json.loads(context_path.read_text())
        validate_context(context)
        if context["mode"] != mode or context["bytes"] != metadata["bytes"]:
            raise ValueError(f"{mode} context does not match the fixture size/mode")
        manifest = verify(build_path)
        binding = json.loads((build_path / "context-binding.json").read_text())
        if (manifest["design"] != design or manifest["baud"] != 9600
                or manifest["clock_hz"] != 50000000 or manifest["fifo_depth"] != 1024
                or binding["context_sha256"] != digest(context_path)
                or binding["context_id"] != context["context_id"]):
            raise ValueError(f"{mode} fitted build does not match the private context/profile")
        specs.append({"mode": mode, "context": str(context_path.resolve()),
                      "context_sha256": digest(context_path), "context_id": context["context_id"],
                      "build": str(build_path.resolve()), "build_manifest_sha256": digest(build_path / "build-manifest.json"),
                      "sof_sha256": manifest["artifacts_sha256"][f"uart_{design}.sof"]})

    base = ROOT / "data/private/de10-2026-10-01"
    fixture = fixture.resolve()
    registry = registry.resolve()
    lines = [
        "# Stored-data replay only: GPS is disconnected; this is NOT live acquisition.",
        "# Wiring: CP2102 TXD -> FPGA V10/RX; FPGA W10/TX -> CP2102 RXD; common GND.",
        "# Disconnect GPS TX/RX and GPS VCC. Do not connect CP2102 VCC. No AD2 is needed.",
        "# Each mode takes about 18.2 minutes at 9600/8N1; timeout=1500 s.",
        "# Run once. A failed secure trial consumes its context/nonce; create a fresh context/build before retrying.",
    ]
    outputs = []
    for spec in specs:
        mode = "baseline" if spec["mode"] == "baseline" else "aes-ctr"
        design = "baseline" if mode == "baseline" else "secure"
        received = base / f"p20-{mode}-1mib-received-01.bin"
        report = base / f"p20-{mode}-1mib-report-01.json"
        if received.exists() or report.exists():
            raise FileExistsError(f"P20 output already exists for {mode}; use new attempt names/context")
        program = command(quartus_bin / "quartus_pgm", "-c", "USB-Blaster [1-3]", "-m", "jtag",
                          "-o", f"p;{Path(spec['build']) / f'uart_{design}.sof'}")
        replay = command(sys.executable, ROOT / "scripts/serial_bench.py", "replay",
                         "--port", port, "--baud", 9600, "--context", spec["context"],
                         *( ["--registry", registry] if mode == "aes-ctr" else [] ),
                         "--input", fixture, "--received", received, "--report", report,
                         "--timeout", 1500)
        lines.extend([f"\n# {mode}: verify successful JTAG programming before replay",
                      program + f" 2>&1 | tee {shlex.quote(str(output / (mode + '-programming.log')))}",
                      replay + " > /dev/null"])
        outputs.append({"mode": spec["mode"], "received": str(received), "report": str(report)})

    plan = {"schema": 1, "status": "PREPARED_NOT_MEASURED", "workload": "stored GPS NMEA replay, not live GPS",
            "baud": 9600, "clock_hz": 50000000, "fifo_bytes": 1024,
            "fixture": str(fixture), "fixture_sha256": digest(fixture), "fixture_bytes": 1048576,
            "modes": specs, "outputs": outputs,
            "criteria": "Each report PASS, exact 1 MiB byte comparison/recovery, zero missing/extra/divergence; never infer live-GPS evidence or FPGA-only latency."}
    output.mkdir(parents=True, exist_ok=False)
    with private_file(output / "campaign.json") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")
    with private_file(output / "commands.txt") as stream:
        stream.write("\n".join(lines) + "\n")
    return {"status": plan["status"], "modes": len(specs), "fixture_sha256": plan["fixture_sha256"],
            "runbook": str(output / "commands.txt"), "note": "Prepared only; no device was programmed or tested."}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("prepare")
    for name in ("fixture", "fixture-report", "baseline-context", "secure-context",
                 "baseline-build", "secure-build", "registry", "output"):
        a.add_argument("--" + name, type=Path, required=True)
    quartus_sh = shutil.which("quartus_sh")
    quartus_bin = Path(quartus_sh).resolve().parent if quartus_sh else None
    a.add_argument("--quartus-bin", type=Path, default=quartus_bin,
                   required=quartus_bin is None)
    a.add_argument("--port", default="/dev/ttyUSB0")
    args = p.parse_args()
    try:
        result = prepare(args.fixture, args.fixture_report, args.baseline_context,
                         args.secure_context, args.baseline_build, args.secure_build,
                         args.registry, args.output, args.quartus_bin, args.port)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL replay campaign: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
