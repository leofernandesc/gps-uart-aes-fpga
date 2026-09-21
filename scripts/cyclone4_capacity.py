#!/usr/bin/env python3
"""Reproducible EP4CE6 capacity study; map/fit only, never assembly/programming."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from build_manifest import digest
from fpga_metrics import _fit_metrics

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    "rtl/common/reset_sync.sv", "rtl/common/sync_fifo.sv",
    "rtl/uart/uart_rx.sv", "rtl/uart/uart_tx.sv",
    "rtl/aes/aes_sbox.sv", "rtl/aes/aes_sub_shift.sv",
    "rtl/aes/aes_mix_columns.sv", "rtl/aes/aes128_next_key.sv", "rtl/aes/aes128_core.sv",
    "rtl/ctr/aes128_ctr_mask.sv", "rtl/ctr/aes128_ctr_stream.sv", "rtl/bridge/uart_ctr_bridge.sv",
    "fpga/de10_lite/common/de10_lite_context_pkg.sv",
    "fpga/de10_lite/common/de10_lite_uart_ctr_top.sv", "fpga/cyclone4/analysis/capacity_top.sv",
]


def main():
    shell = os.environ.get("QUARTUS_SH") or shutil.which("quartus_sh") or "/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_sh"
    binary = Path(shell).parent
    if not (binary / "quartus_map").is_file() or not (binary / "quartus_fit").is_file():
        raise ValueError("Quartus map/fit not found; set QUARTUS_SH")
    output = ROOT / "build/cyclone4/capacity"
    output.mkdir(parents=True, exist_ok=True)
    hashes = {name: digest(ROOT / name) for name in SOURCES + ["fpga/cyclone4/analysis/capacity.sdc", "scripts/cyclone4_capacity.py"]}
    result = {"kind": "capacity_only", "device": "EP4CE6E22C8", "clock_hz_assumed": 48_000_000,
              "board_confirmed": False, "clock_confirmed": False, "physical_pins_assigned": False,
              "timing_audited": False, "sof_generated": False, "logic_elements_available": 6272,
              "seed": 1, "sources_sha256": hashes, "designs": {},
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "started_utc": datetime.now(timezone.utc).isoformat()}
    # Invalidate a previous summary before invoking either compiler.
    summary = output / "capacity.json"
    result["status"] = "RUNNING"
    summary.write_text(json.dumps(result, indent=2) + "\n")
    for design, enabled in (("baseline", 0), ("secure", 1)):
        path = output / design
        path.mkdir(exist_ok=True)
        if list(path.rglob("*.sof")):
            raise ValueError(f"Unexpected SOF in analysis directory: {path}; inspect manually")
        assignments = [
            'set_global_assignment -name FAMILY "Cyclone IV E"',
            'set_global_assignment -name DEVICE EP4CE6E22C8',
            'set_global_assignment -name TOP_LEVEL_ENTITY capacity_top',
            'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY .',
            'set_global_assignment -name NUM_PARALLEL_PROCESSORS 2',
            'set_global_assignment -name SEED 1',
            f'set_parameter -name ENABLE_AES {enabled}',
        ]
        assignments.extend(f'set_global_assignment -name SYSTEMVERILOG_FILE "{ROOT / name}"' for name in SOURCES)
        assignments.append(f'set_global_assignment -name SDC_FILE "{ROOT / "fpga/cyclone4/analysis/capacity.sdc"}"')
        assignments.extend(f'set_instance_assignment -name VIRTUAL_PIN ON -to "{name}"' for name in ("reset_n", "rx", "tx", "status[*]"))
        # The fitter chooses an analysis clock location; no board pin is asserted.
        (path / "capacity.qsf").write_text("\n".join(assignments) + "\n")
        (path / "capacity.qpf").write_text('PROJECT_REVISION = "capacity"\n')
        rc = 0
        for phase in ("map", "fit"):
            with (path / f"{phase}.log").open("w") as log:
                rc = subprocess.run([str(binary / f"quartus_{phase}"), "--read_settings_files=on", "--write_settings_files=off", "capacity"], cwd=path, stdout=log, stderr=subprocess.STDOUT).returncode
            print(f"{design}: {phase} {'PASS' if rc == 0 else 'FAIL'}; {path / f'{phase}.log'}", flush=True)
            if rc:
                break
        if rc:
            result["designs"][design] = {"status": "FAIL", "exit_code": rc}
        else:
            metrics = _fit_metrics(path)
            metrics.update(status="PASS", artifacts_sha256={p.name: digest(p) for p in path.glob("*.fit.summary")})
            result["designs"][design] = metrics
            print(f"{design}: {metrics['logic_elements']} / 6272 LE; {metrics['registers']} registers; capacity only", flush=True)
    if hashes != {name: digest(ROOT / name) for name in hashes}:
        raise ValueError("Sources changed during capacity study; repeat both builds")
    result["status"] = "PASS" if all(d["status"] == "PASS" for d in result["designs"].values()) else "FAIL"
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    summary.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{result['status']}: EP4CE6 capacity study; no board timing validation, no SOF, no programming")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
