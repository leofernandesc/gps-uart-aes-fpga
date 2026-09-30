#!/usr/bin/env python3
"""Audit the selected fits and separately refit explicit synchronizer profiles.

The published builds, contexts and snapshots are never overwritten. The new
profiles are analysis-only; they are not replacements for tested bitstreams.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from build_manifest import digest
from fpga_metrics import DEFAULT_BUILD, ROOT, _fit_metrics, _timing_metrics
from manuscript_check import SNAPSHOT, check_builds, load_metrics


RX_CHAIN = "de10_lite_uart_ctr_top:implementation|uart_ctr_bridge:bridge_inst|uart_rx:rx_inst"
RESET_CHAIN = "de10_lite_uart_ctr_top:implementation|reset_sync:reset_inst"
RX_TOGGLE_HZ = 38_400
# Conservative analysis assumption, not a measurement of KEY0 bounce/activity.
RESET_TOGGLE_HZ = 6_250_000
RECORD = re.compile(r"REVIEW corner=([1-3]) check=min_pulse_width slack_ns=([-+0-9.eE]+)")


def pulse_results(path):
    text = (path / "review.log").read_text()
    if len(re.findall(r"^PASS: 3 supplemental timing corners audited$", text, re.M)) != 1:
        raise ValueError("supplemental STA did not pass")
    if re.search(r"^(?:Error|FAIL)\b", text, re.M):
        raise ValueError("supplemental STA reported an error")
    slacks = {}
    for line in text.splitlines():
        if not line.startswith("REVIEW"):
            continue
        match = RECORD.fullmatch(line)
        if not match:
            raise ValueError("malformed pulse width evidence")
        corner, value = int(match[1]), float(match[2])
        if corner in slacks or not math.isfinite(value) or value < 0:
            raise ValueError("duplicate/nonfinite/negative pulse width slack")
        slacks[corner] = value
    if set(slacks) != {1, 2, 3}:
        raise ValueError("missing pulse width corner")
    return {"slack_ns_by_corner": [slacks[c] for c in (1, 2, 3)], "slack_ns_min": min(slacks.values())}


def metastability_results(path, identified=False):
    results = []
    for corner in (1, 2, 3):
        text = (path / f"metastability_corner{corner}.rpt").read_text()
        count = re.search(r"^Number of Synchronizer Chains Found: (\d+)$", text, re.M)
        if not count or int(count[1]) != 2:
            raise ValueError("expected exactly RX and reset synchronizer chains")
        chains = []
        blocks = re.split(r"\nSynchronizer Chain #\d+:", text)[1:]
        if len(blocks) != 2:
            raise ValueError("missing full synchronizer chain statistics")
        for block in blocks:
            def field(name):
                found = re.search(rf"^;\s*{re.escape(name)}\s*;\s*([^;]+?)\s*;", block, re.M)
                if not found:
                    raise ValueError(f"missing synchronizer field: {name}")
                return found[1].strip()
            source = field("Source Node")
            if source not in {"UART_RX", "KEY0_N"}:
                raise ValueError("unexpected asynchronous source")
            chain = {"source": source, "head": field("Synchronization Node"),
                     "registers": int(field("Number of Synchronization Registers in Chain")),
                     "identification": field("Method of Synchronizer Identification"),
                     "settling_ns": float(field("Available Settling Time (ns)")),
                     "toggle_millions_per_second": float(field("Data Toggle Rate Used in MTBF Calculation (millions of transitions / sec)")),
                     "worst_mtbf_years": field("Worst-Case MTBF (years)"),
                     "typical_mtbf_years": field("Typical MTBF (years)"),
                     "included_in_design_mtbf": field("Included in Design MTBF")}
            expected_head = f"{RX_CHAIN}|rx_meta" if source == "UART_RX" else f"{RESET_CHAIN}|release_pipe[0]"
            if chain["head"] != expected_head or chain["registers"] != 2:
                raise ValueError("unexpected synchronizer head or length")
            if not math.isfinite(chain["settling_ns"]) or chain["settling_ns"] <= 0:
                raise ValueError("invalid synchronizer settling time")
            if identified:
                if chain["identification"] != "User Specified":
                    raise ValueError("explicit synchronizer assignment not recognized")
                expected_rate = RX_TOGGLE_HZ if source == "UART_RX" else RESET_TOGGLE_HZ
                if not math.isclose(chain["toggle_millions_per_second"], expected_rate / 1e6, abs_tol=5e-5):
                    raise ValueError("synchronizer toggle assumption not applied")
            chains.append(chain)
        if {c["source"] for c in chains} != {"UART_RX", "KEY0_N"}:
            raise ValueError("duplicate/missing synchronizer source")
        results.append({"corner": corner, "chains": sorted(chains, key=lambda c: c["source"])})
    return results


def identified_qsf(source, output, design):
    """Resolve all file inputs before creating an isolated analysis project."""
    text = source.read_text()
    def replace_file(match):
        prefix, value = match.groups()
        resolved = (source.parent / value.strip('"')).resolve()
        if not resolved.is_file():
            raise ValueError(f"missing Quartus input: {resolved}")
        return prefix + '"' + str(resolved) + '"'
    text = re.sub(r"^(set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|SDC)_FILE\s+)(.+)$", replace_file, text, flags=re.M)
    text = re.sub(r"^set_global_assignment -name PROJECT_OUTPUT_DIRECTORY .+$",
                  f'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY "{output}"', text, flags=re.M)
    # Scope identification to the four actual synchronization registers only.
    for register in (f"{RX_CHAIN}|rx_meta", f"{RX_CHAIN}|rx_sync",
                     f"{RESET_CHAIN}|release_pipe[0]", f"{RESET_CHAIN}|release_pipe[1]"):
        # QSF's assignment reader treats Tcl braces as literal node characters.
        text += f'\nset_instance_assignment -name SYNCHRONIZER_IDENTIFICATION "FORCED IF ASYNCHRONOUS" -to "{register}"'
    text += f'\nset_instance_assignment -name SYNCHRONIZER_TOGGLE_RATE {RX_TOGGLE_HZ} -to "{RX_CHAIN}|rx_meta"'
    text += f'\nset_instance_assignment -name SYNCHRONIZER_TOGGLE_RATE {RESET_TOGGLE_HZ} -to "{RESET_CHAIN}|release_pipe[0]"\n'
    qsf = output / f"uart_{design}.qsf"
    qsf.write_text(text)
    return qsf


def run(command, cwd, log):
    # Generated tool logs are local evidence, not source edits.
    with log.open("x") as stream:
        process = subprocess.run([str(arg) for arg in command], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if process.returncode:
        raise ValueError(f"Quartus failed ({process.returncode}); inspect {log}")
    if re.search(r"^Critical Warning\b", log.read_text(), re.M):
        raise ValueError(f"Quartus critical warning; inspect {log}")


def review(output, quartus_sh, snapshot=SNAPSHOT, build_root=DEFAULT_BUILD, identify=True):
    metrics = load_metrics(snapshot)
    if not check_builds(metrics, build_root):
        raise ValueError("the selected fitted databases and artifacts must be present")
    quartus_sta = quartus_sh.with_name("quartus_sta")
    if not quartus_sh.is_file() or not quartus_sta.is_file():
        raise ValueError("Quartus executables not found")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    scripts = [ROOT / "scripts" / name for name in ("timing_review.py", "quartus_timing_review.tcl", "quartus_timing.tcl",
                                                    "build_manifest.py", "fpga_metrics.py", "manuscript_check.py")]
    evidence = {"schema": 1, "status": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat(),
                "selected_snapshot_sha256": digest(snapshot), "analysis_sources_sha256": {str(p.relative_to(ROOT)): digest(p) for p in scripts},
                "assumptions": {"uart_rx_toggle_hz": RX_TOGGLE_HZ, "key0_toggle_hz": RESET_TOGGLE_HZ,
                                "key0_note": "Conservative analysis assumption, not measured button activity",
                                "uart_note": "One transition per bit at 38400 baud; electrical noise is not modeled"},
                "designs": {}}
    for design in ("baseline", "secure"):
        project_dir = ROOT / "fpga/de10_lite" / design
        project = f"uart_{design}"
        original = output / design / "selected-fit"
        original.mkdir(parents=True)
        print(f"REVIEW {design}: selected post-fit pulse width and synchronization", flush=True)
        # Re-run the existing four-check audit too, without touching its reports.
        run([quartus_sta, "-t", scripts[2], project, original], project_dir, original / "timing-audit.log")
        for report in (build_root / design).glob("*.fit.summary"):
            shutil.copyfile(report, original / report.name)
        reproduced = _timing_metrics(original)
        selected = metrics["designs"][design]
        for field in reproduced:
            if reproduced[field] != selected[field]:
                raise ValueError(f"{design}: fitted database differs from selected timing: {field}")
        run([quartus_sta, "-t", scripts[1], project, original], project_dir, original / "review.log")
        entry = {"selected_sof_sha256": next(v for n, v in selected["provenance"]["artifacts_sha256"].items() if n.endswith(".sof")),
                 "selected_fit": {"pulse_width": pulse_results(original), "synchronizers": metastability_results(original)}}
        if identify:
            separate = output / design / "identified-profile"
            separate.mkdir()
            qsf = identified_qsf(project_dir / f"{project}.qsf", separate, design)
            print(f"REVIEW {design}: refitting isolated explicit-synchronizer profile (not programmed)", flush=True)
            run([quartus_sh, "--flow", "compile", project], separate, separate / "compile.log")
            run([quartus_sta, "-t", scripts[2], project, separate], separate, separate / "timing-audit.log")
            run([quartus_sta, "-t", scripts[1], project, separate], separate, separate / "review.log")
            entry["identified_profile"] = {"fit": _fit_metrics(separate), "timing": _timing_metrics(separate),
                                            "pulse_width": pulse_results(separate),
                                            "synchronizers": metastability_results(separate, identified=True),
                                            "qsf_sha256": digest(qsf), "sof_sha256": digest(separate / f"{project}.sof"),
                                            "note": "Analysis-only profile; not the physically tested bitstream"}
        evidence["designs"][design] = entry
    # Confirm that neither original builds nor analysis inputs changed mid-run.
    check_builds(metrics, build_root)
    if any(digest(ROOT / name) != value for name, value in evidence["analysis_sources_sha256"].items()):
        raise ValueError("analysis sources changed during review")
    evidence["artifacts_sha256"] = {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*"))
                                    if p.is_file() and p.suffix in {".rpt", ".log", ".sof", ".summary"}}
    evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
    evidence["status"] = "PASS"
    with (output / "review.json").open("x") as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"PASS: supplementary timing review; evidence: {output / 'review.json'}", flush=True)
    return evidence


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwrites a review")
    parser.add_argument("--quartus-sh", type=Path, default=Path(shutil.which("quartus_sh") or "/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_sh"))
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--selected-only", action="store_true", help="No refit; inspect only the selected builds")
    args = parser.parse_args()
    try:
        review(args.output, args.quartus_sh, args.snapshot, args.build_root, identify=not args.selected_only)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL timing review: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
