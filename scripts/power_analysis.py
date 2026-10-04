#!/usr/bin/env python3
"""Isolated MAX 10 post-fit export and strict Power Analyzer evidence review.

No synthesis, programming, license bypass, or automatic paper promotion.
Reports with default activity are retained but rejected for publication.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from build_manifest import ROOT, digest, verify

POWER_FIELDS = {"total_mw": "Total Thermal Power Dissipation",
                "dynamic_mw": "Core Dynamic Thermal Power Dissipation",
                "static_mw": "Core Static Thermal Power Dissipation",
                "io_mw": "I/O Thermal Power Dissipation"}


def parse_report(text):
    rows = [list(map(str.strip, line.split(";")[1:-1]))
            for line in text.splitlines() if line.startswith(";")]
    def row(label):
        matches = [r for r in rows if r and r[0] == label]
        if len(matches) != 1:
            raise ValueError(f"missing/ambiguous power report field: {label}")
        return matches[0][1:]
    values = {}
    for name, label in POWER_FIELDS.items():
        m = re.fullmatch(r"([\d.]+)\s*(mW|W)", row(label)[0])
        if not m:
            raise ValueError(f"unsupported power units: {label}")
        values[name] = float(m[1]) * (1000 if m[2] == "W" else 1)
    values["confidence"] = row("Power Estimation Confidence")[0]
    values["device"] = row("Device")[0]
    values["models"] = row("Power Models")[0]
    coverage = row("-- Number of signals with Toggle Rate from Simulation")
    def percentage(cell):
        m = re.search(r"\(([\d.]+)%\)", cell)
        if not m:
            raise ValueError("missing activity coverage")
        return float(m[1])
    values["coverage_percent"] = dict(zip(
        ("all", "pins", "registered", "combinational"), map(percentage, coverage)))
    unknown = row("-- Simulation time nodes in unknown state")[0]
    if not re.fullmatch(r"[\d.]+%", unknown):
        raise ValueError("missing unknown-state percentage")
    values["unknown_percent"] = float(unknown.rstrip("%"))
    values["settings"] = {r[0]: r[1] for r in rows if len(r) >= 2 and r[0] in (
        "Automatically Compute Junction Temperature", "Specified Junction Temperature",
        "Device Power Characteristics", "Use vectorless estimation", "Use Input Files")}
    values["pin_activity"] = {r[0]: {"type": r[1], "toggle_source": r[3],
        "static_probability_source": r[5]} for r in rows if len(r) >= 6 and
        r[1] in ("Input Pin", "Output Pin", "Bidirectional Pin")}
    return values


def acceptance(report, evidence):
    reasons = []
    if not report["confidence"].lower().startswith("high"):
        reasons.append("Power Analyzer confidence is not High")
    if report["device"] != "10M50DAF484C7G" or report["models"] != "Final":
        reasons.append("wrong device or non-final power model")
    if report["coverage_percent"]["registered"] < 95:
        reasons.append("registered-node simulation activity coverage below 95%")
    # MAX 10 has reserved/JTAG pins beyond this design's I/O. Require every
    # pin used by this data path to come from simulation, not the aggregate
    # device-pin percentage; combinational nodes may use Quartus vectorless
    # propagation only when the overall tool confidence is High.
    required_pins = {"MAX10_CLK1_50", "KEY0_N", "UART_RX", "UART_TX"}
    required_pins.update(f"LEDR[{i}]" for i in range(10))
    for name in sorted(required_pins):
        activity = report["pin_activity"].get(name)
        if not activity or not activity["toggle_source"].startswith("Simulation") or \
                not activity["static_probability_source"].startswith("Simulation"):
            reasons.append(f"used I/O pin lacks simulation activity: {name}")
    if report["unknown_percent"] != 0:
        reasons.append("unknown states in analyzed window")
    # These are project acceptance thresholds, NOT vendor accuracy guarantees.
    for field in ("byte_exact", "clock_io_mapping_verified", "steady_state",
                  "postfit_functional_simulation", "same_workload_verified"):
        if evidence.get(field) is not True:
            reasons.append(f"missing evidence: {field}")
    change = evidence.get("doubling_dynamic_change_percent")
    if not isinstance(change, (int, float)) or not math.isfinite(change) or not 0 <= change < 5:
        reasons.append("duration-doubling dynamic convergence not within 5%")
    settings = report["settings"]
    if settings.get("Automatically Compute Junction Temperature") != "Off":
        reasons.append("junction temperature not held fixed")
    if settings.get("Device Power Characteristics") != "TYPICAL":
        reasons.append("process characteristics not Typical")
    if not evidence.get("artifacts_sha256"):
        reasons.append("evidence artifacts not bound by hashes")
    return reasons


def review(report_path, evidence_path=None):
    report = parse_report(report_path.read_text())
    evidence = json.loads(evidence_path.read_text()) if evidence_path else {}
    if evidence_path:
        for name, expected in evidence.get("artifacts_sha256", {}).items():
            path = (evidence_path.parent / name).resolve()
            if not path.is_relative_to(evidence_path.parent.resolve()) or digest(path) != expected:
                raise ValueError("modified/unsafe power evidence artifact")
        if evidence.get("power_report_sha256") != digest(report_path):
            raise ValueError("power report is not bound to evidence")
    reasons = acceptance(report, evidence)
    return {"schema": 1, "status": "ACCEPTED_ESTIMATE" if not reasons else "EXPLORATORY_ONLY",
            "publishable": not reasons, "invalid_reasons": reasons,
            "report_sha256": digest(report_path), "power": report,
            "evidence": evidence,
            "note": "Estimated FPGA thermal power, not board power or a physical measurement."}


def run(command, cwd, log):
    with log.open("x") as stream:
        result = subprocess.run(list(map(str, command)), cwd=cwd,
                                stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode or re.search(r"^(?:Error|Critical Warning)\b", log.read_text(), re.M):
        raise ValueError(f"tool failed; inspect {log}")


def segment(project_dir, vcd, output, quartus_bin):
    """Consume one closed VCD and archive it compressed before next segment."""
    import gzip
    project = next(project_dir.glob("uart_*.qpf")).stem
    output.mkdir(parents=True, exist_ok=False)
    vcd_hash = digest(vcd)
    run([quartus_bin / "quartus_pow", project, "--estimate_power=on",
         f"--input_vcd={vcd.resolve()}", "--vcd_filter_glitches=on",
         "--write_settings_files=off"], project_dir, output / "power.log")
    report = project_dir / (project + ".pow.rpt")
    shutil.copyfile(report, output / "power.rpt")
    shutil.copyfile(project_dir / (project + ".pow.summary"), output / "power.summary")
    parsed = parse_report(report.read_text())
    compressed = output / "activity.vcd.gz"
    with vcd.open("rb") as source, gzip.open(compressed, "wb", compresslevel=1) as dest:
        shutil.copyfileobj(source, dest)
    # Check the archived bytes before retiring the regenerable uncompressed segment.
    import hashlib
    hasher = hashlib.sha256()
    with gzip.open(compressed, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    if hasher.hexdigest() != vcd_hash:
        raise ValueError("compressed VCD verification failed; original retained")
    vcd.unlink()
    (output / "segment.json").write_text(json.dumps({"vcd_sha256": vcd_hash,
        "archive_sha256": digest(compressed), "report_sha256": digest(output / "power.rpt"),
        "power": parsed}, indent=2) + "\n")
    return parsed


def prepare(baseline, aes, output, quartus_bin):
    manifests = [verify(p) for p in (baseline, aes)]
    if [m["design"] for m in manifests] != ["baseline", "secure"]:
        raise ValueError("expected baseline and AES fits in that order")
    for field in ("device", "clock_hz", "baud", "fifo_depth", "seed", "shared_rtl_sha256"):
        if manifests[0][field] != manifests[1][field]:
            raise ValueError(f"unmatched fits: {field}")
    output = output.resolve()
    if not output.is_relative_to(ROOT / "build/power-analysis"):
        raise ValueError("new power output must be below build/power-analysis")
    output.mkdir(parents=True, exist_ok=False)
    metadata = {"schema": 1, "status": "NETLISTS_PREPARED_NOT_SIMULATED",
                "conditions": {"clock_hz": 50000000, "baud": 9600,
                    "process": "TYPICAL", "junction_celsius": [25, 50, 70],
                    "uart_tx_load_pf": [5, 10, 15],
                    "load_note": "Board-model far-end capacitance assumptions, not measured board loads; LEDs retain fitter defaults.",
                    "supply": "Device/fitter defaults; retain voltage tables from each report"},
                "workloads": ["idle", "live GPS with observed byte gaps", "saturated NMEA"],
                "publication_gate": "High confidence, >=95% registered-node simulation activity, "
                    "simulation-derived activity on all used I/O pins, "
                    "zero X/Z, independent byte verification, fixed conditions and <5% duration sensitivity",
                "builds": {}}
    for source, manifest in zip((baseline, aes), manifests):
        label = "baseline" if manifest["design"] == "baseline" else "aes-ctr"
        clone = output / label
        shutil.copytree(source, clone)
        project = f"uart_{manifest['design']}"
        qsf = clone / (project + ".qsf")
        text = re.sub(r'^set_global_assignment -name PROJECT_OUTPUT_DIRECTORY .+$',
                      f'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY "{clone}"',
                      qsf.read_text(), flags=re.M)
        qsf.write_text(text)
        run([quartus_bin / "quartus_eda", project, "--simulation=on", "--tool=questasim",
             "--format=verilog", f"--output_directory={clone / 'netlist'}", "--vcd_type=all",
             "--glitch_filtering=on", "--maintain_design_hierarchy=on",
             "--vcd_tb_design_instance_name=/tb/dut", "--write_settings_files=off"], clone,
            clone / "postfit-export.log")
        metadata["builds"][label] = {"original": str(source.resolve()),
            "original_manifest_sha256": digest(source / "build-manifest.json"),
            "netlist_sha256": digest(clone / "netlist" / (project + ".vo")),
            "project": project, "top": f"de10_lite_uart_{manifest['design']}_top"}
        # Settings modify only the clone. Invocation arguments are temperature and UART load.
        (clone / "conditions.tcl").write_text(
            'package require ::quartus::project\n'
            f'project_open {project}\n'
            'set_global_assignment -name POWER_USE_DEVICE_CHARACTERISTICS TYPICAL\n'
            'set_global_assignment -name POWER_AUTO_COMPUTE_TJ OFF\n'
            'set_global_assignment -name POWER_TJ_VALUE [lindex $quartus(args) 0]\n'
            'set_instance_assignment -name BOARD_MODEL_FAR_C [format "%sP" [lindex $quartus(args) 1]] -to UART_TX\n'
            'set_global_assignment -name POWER_REPORT_SIGNAL_ACTIVITY ON\n'
            'export_assignments\nproject_close\n')
        # Re-check original inputs/artifacts after the export to catch accidental mutation.
        verify(source)
    (output / "preparation.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--baseline", type=Path, required=True)
    a.add_argument("--aes", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    quartus_sh = shutil.which("quartus_sh")
    quartus_bin = Path(quartus_sh).resolve().parent if quartus_sh else None
    a.add_argument("--quartus-bin", type=Path, default=quartus_bin,
                   required=quartus_bin is None)
    a = sub.add_parser("review")
    a.add_argument("--report", type=Path, required=True)
    a.add_argument("--evidence", type=Path)
    a.add_argument("--output", type=Path, required=True)
    a = sub.add_parser("segment", help="internal sequential Questa VCD consumer")
    a.add_argument("--project-dir", type=Path, required=True)
    a.add_argument("--vcd", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--quartus-bin", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.action == "prepare":
            result = prepare(args.baseline, args.aes, args.output, args.quartus_bin)
        elif args.action == "review":
            result = review(args.report, args.evidence)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as f:
                json.dump(result, f, indent=2)
        else:
            result = segment(args.project_dir, args.vcd, args.output, args.quartus_bin)
        print(json.dumps(result, indent=2))
        return 0 if result.get("publishable", args.action != "review") else 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL power analysis: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
