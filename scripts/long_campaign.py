#!/usr/bin/env python3
"""Prepare interleaved physical trials; preparation is never a bench PASS."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

from build_manifest import ROOT, digest
from capture import private_file
from context import create_context
from live_timing import frame_metrics


DEFAULT_CP2102_PORT = (
    "/dev/serial/by-id/"
    "usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"
)


def command(*parts):
    return shlex.join(map(str, parts))


def prepare(output, registry, quartus_bin, live_bytes=65536, trials=3,
            port=DEFAULT_CP2102_PORT):
    output = output.resolve()
    if not output.is_relative_to(ROOT / "data/private"):
        raise ValueError("campaign must live below data/private")
    if live_bytes < 1024 or not 1 <= trials <= 10:
        raise ValueError("invalid campaign length/trials")
    # Exclusive directory: never replace a capture or a secure context.
    output.mkdir(parents=True, exist_ok=False)
    campaign = {"schema": 1, "status": "PREPARED_NOT_MEASURED", "baud": 9600,
                "clock_hz": 50000000, "fifo_bytes": 1024, "sample_rate_hz": 200000,
                "live_bytes": live_bytes, "trials_per_mode": trials, "port": port,
                "runs": []}
    baseline = output / "baseline-context.json"
    create_context("baseline", live_bytes, baseline)
    base_build = ROOT / "build/experiments" / (output.name + "-baseline")
    build_commands = [command(sys.executable, ROOT / "scripts/bench_build.py",
        "--context", baseline, "--output", base_build, "--quartus-sh", quartus_bin / "quartus_sh")]
    bench = ["# Run from the project root. Commands are instructions, not automatically executed.",
             "# Close WaveForms. Live: DIO0=GPS TX/V10, DIO2=FPGA TX/W10, CP RXD=W10.",
             f"# CP2102 port: {port}",
             "# CP TXD disconnected; common GND. Isolate GPS TX until READY.",
             "# Keep the GPS powered at 9600; reconnect TX only after READY.",
             "# No KEY0 reset. Confirm LEDs only if actually observed inactive.",
             "# After each run, require analyze PASS before continuing; stop on FAIL.",
             "# Each secure attempt requires a fresh context/build, including after failure."]
    for trial in range(1, trials + 1):
        for mode in ("baseline", "aes-128-ctr"):
            label = "baseline" if mode == "baseline" else "aes-ctr"
            context = baseline
            build = base_build
            if mode != "baseline":
                context = output / f"{label}-{trial:02d}-context.json"
                create_context(mode, live_bytes, context, registry, random_key=True)
                build = ROOT / "build/experiments" / f"{output.name}-{label}-{trial:02d}"
                build_commands.append(command(sys.executable, ROOT / "scripts/bench_build.py",
                    "--context", context, "--output", build, "--quartus-sh", quartus_bin / "quartus_sh"))
            capture = output / f"{label}-{trial:02d}-capture"
            design = "baseline" if mode == "baseline" else "secure"
            run = {"mode": mode, "trial": trial, "context": str(context),
                   "context_sha256": digest(context), "build": str(build), "capture": str(capture)}
            campaign["runs"].append(run)
            bench += [f"\n# {label} trial {trial}: GPS TX isolated before programming",
                command(quartus_bin / "quartus_pgm", "-c", "USB-Blaster [1-3]", "-m", "jtag",
                        "-o", f"p;{build}/uart_{design}.sof") +
                f" 2>&1 | tee {shlex.quote(str(output / (label + '-' + str(trial) + '-programming.log')))}",
                command(sys.executable, ROOT / "scripts/ad2_live_capture.py", "record",
                        "--port", port, "--context", context, "--build", build,
                        "--output", capture, "--rate", 200000, "--baud", 9600,
                        "--timeout", 600, "--tx-dio", 2, "--confirm-source-inactive",
                        "--confirm-txd-disconnected", *(["--registry", registry] if mode != "baseline" else [])),
                "# Analyze only after checking LED6, LED7 and no reset throughout this trial:",
                command(sys.executable, ROOT / "scripts/ad2_live_capture.py", "analyze",
                        "--input", capture, "--context", context, "--confirm-led6-off",
                        "--confirm-led7-off", "--confirm-no-reset")]
    with private_file(output / "campaign.json") as f:
        json.dump(campaign, f, indent=2)
    with private_file(output / "build-commands.sh") as f:
        f.write("#!/usr/bin/env bash\nset -euo pipefail\n" + "\n".join(build_commands) + "\n")
    with private_file(output / "bench-commands.txt") as f:
        f.write("\n".join(bench) + "\n")
    return campaign


def summarize(manifest):
    from ad2_live_capture import assess
    campaign = json.loads(manifest.read_text())
    results = []
    for run in campaign["runs"]:
        capture = Path(run["capture"])
        item = {"mode": run["mode"], "trial": run["trial"], "status": "PENDING"}
        try:
            if digest(run["context"]) != run["context_sha256"]:
                raise ValueError("campaign context modified")
            acquisition = json.loads((capture / "acquisition.json").read_text())
            comparison = json.loads((capture / "comparison.json").read_text())
            context = json.loads(Path(run["context"]).read_text())
            if acquisition["context_sha256"] != run["context_sha256"]:
                raise ValueError("capture/context mismatch")
            if comparison["acquisition_sha256"] != digest(capture / "acquisition.json"):
                raise ValueError("comparison/acquisition mismatch")
            for name in ("reference.bin", "cipher.bin", "cp2102.bin"):
                if digest(capture / name) != acquisition["artifacts_sha256"][name]:
                    raise ValueError("capture modified")
            verified, _ = assess(*[(capture / n).read_bytes() for n in
                ("reference.bin", "cipher.bin", "cp2102.bin")], context, acquisition)
            observations = comparison.get("operator_observations", {})
            if verified["status"] != "PASS" or comparison["status"] != "PASS" or not all(
                    observations.get(n) is True for n in ("overflow_off", "framing_off", "no_reset")):
                raise ValueError("byte verification/operator evidence not PASS")
            item.update(status="PASS", bytes=context["bytes"],
                        nmea=verified["reference_nmea"]["sentences"],
                        metrics=frame_metrics(acquisition, context["bytes"]))
        except FileNotFoundError:
            pass
        except (ValueError, KeyError) as exc:
            item.update(status="FAIL", reason=str(exc))
        results.append(item)
    return {"status": "PASS" if all(r["status"] == "PASS" for r in results) and results else "INCOMPLETE",
            "runs": results, "note": "Each run independently verified; no byte trimming/realignment."}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--registry", type=Path, default=ROOT / "data/private/nonce-registry.json")
    quartus_sh = shutil.which("quartus_sh")
    quartus_bin = Path(quartus_sh).resolve().parent if quartus_sh else None
    a.add_argument("--quartus-bin", type=Path, default=quartus_bin,
                   required=quartus_bin is None)
    a.add_argument("--bytes", type=int, default=65536)
    a.add_argument("--trials", type=int, default=3)
    a.add_argument("--port", default=DEFAULT_CP2102_PORT,
                   help="CP2102 serial path; prefer /dev/serial/by-id over ttyUSB numbering")
    a = sub.add_parser("summarize")
    a.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    try:
        result = (prepare(args.output, args.registry, args.quartus_bin, args.bytes,
                          args.trials, args.port)
                  if args.action == "prepare" else summarize(args.manifest))
        print(json.dumps(result, indent=2))
        return 0 if result["status"] in ("PASS", "PREPARED_NOT_MEASURED") else 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL campaign: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
