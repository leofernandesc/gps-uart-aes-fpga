#!/usr/bin/env python3
"""Bind Quartus results to the exact inputs and artifacts (never store key text)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
NAME = "build-manifest.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _inside(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"manifest path escapes its root: {name}")
    return path


def _save(path, manifest):
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def begin(qsf, output, board, design):
    qsf = qsf.resolve()
    contents = qsf.read_text(encoding="utf-8")
    inputs = {qsf, qsf.with_suffix(".qpf"), ROOT / "scripts/quartus_timing.tcl"}
    for name in re.findall(r"^set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|SDC)_FILE\s+(\S+)\s*$", contents, re.M):
        inputs.add((qsf.parent / name.strip('"')).resolve())
    sources = {str(p.relative_to(ROOT)): digest(p) for p in sorted(inputs)}
    shared = {name: value for name, value in sources.items()
              if name.startswith("rtl/") or name.startswith("fpga/de10_lite/common/")
              or name.startswith("fpga/cyclone4/common/")}
    device = re.search(r"-name DEVICE (\S+)", contents).group(1)
    seed = int(re.search(r"-name SEED (\d+)", contents).group(1))
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(["git", "diff", "HEAD", "--", "rtl", "fpga"], cwd=ROOT)
    manifest = {
        "schema": 1, "status": "RUNNING", "board": board, "design": design,
        "device": device, "seed": seed,
        "clock_hz": 50_000_000 if board == "de10_lite" else 48_000_000,
        "baud": 9600, "fifo_depth": 1024,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "commit": revision, "tracked_rtl_config_dirty": bool(diff),
        "rtl_config_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "sources_sha256": sources,
        "shared_rtl_sha256": hashlib.sha256(json.dumps(shared, sort_keys=True).encode()).hexdigest(),
    }
    _save(output / NAME, manifest)


def verify(path, source_root=ROOT, require_complete=True):
    manifest = json.loads((path / NAME).read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or (require_complete and manifest.get("status") != "PASS"):
        raise ValueError(f"{path}: incomplete/unsupported build manifest")
    if not manifest.get("sources_sha256"):
        raise ValueError(f"{path}: missing source hashes")
    for name, expected in manifest["sources_sha256"].items():
        if digest(_inside(source_root, name)) != expected:
            raise ValueError(f"{path}: stale build; source changed: {name}")
    if require_complete:
        artifacts = manifest.get("artifacts_sha256", {})
        required = {"timing-audit.log", "clocks.rpt", "check_timing.rpt", "unconstrained.rpt", "tool-version.txt", "compile.log"}
        if not required <= artifacts.keys() or not any(n.endswith(".sof") for n in artifacts):
            raise ValueError(f"{path}: incomplete artifact hashes")
        reports = {p.name for pattern in ("*.fit.summary", "fmax_corner*.rpt") for p in path.glob(pattern)}
        hashed_reports = {n for n in artifacts if n.endswith(".fit.summary") or re.fullmatch(r"fmax_corner\d+\.rpt", n)}
        if reports != hashed_reports:
            raise ValueError(f"{path}: artifact report set changed")
        for name, expected in artifacts.items():
            if digest(_inside(path, name)) != expected:
                raise ValueError(f"{path}: artifact hash mismatch: {name}")
    return manifest


def finish(path):
    manifest = verify(path, require_complete=False)
    artifacts = {p for pattern in ("*.fit.summary", "*.sof", "fmax_corner*.rpt") for p in path.glob(pattern)}
    artifacts.update(path / name for name in ("timing-audit.log", "clocks.rpt", "check_timing.rpt", "unconstrained.rpt", "tool-version.txt", "compile.log"))
    manifest["artifacts_sha256"] = {p.name: digest(p) for p in sorted(artifacts)}
    manifest["status"] = "PASS"
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    _save(path / NAME, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("begin", "finish"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qsf", type=Path)
    parser.add_argument("--board")
    parser.add_argument("--design")
    args = parser.parse_args()
    if args.action == "begin":
        if not args.qsf or args.board not in ("de10_lite", "cyclone4") or args.design not in ("baseline", "secure"):
            parser.error("begin requires a DE10-Lite or Cyclone IV baseline/secure QSF")
        begin(args.qsf, args.output, args.board, args.design)
    else:
        finish(args.output)


if __name__ == "__main__":
    main()
