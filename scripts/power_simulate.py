#!/usr/bin/env python3
"""Questa post-fit functional UART stimulus with bounded, archived VCD captures.

Uses official encrypted MAX 10 models. A completed simulation is not an
accepted power result until mapping and duration convergence are reviewed.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys

from build_manifest import ROOT, digest, verify
from ctr_vectors import crypt
from power_analysis import run, segment
from stress_fixture import make_payload

MAX_SEGMENT_MS = 2


def tcl(value):
    value = str(value)
    if any(c in value for c in "{}\n\r"):
        raise ValueError("unsafe Tcl path")
    return "{" + value + "}"


def workload(capture, kind, start, duration):
    """Retain observed GPS byte gaps; never realign a failed capture."""
    reference = (capture / "reference.bin").read_bytes()
    comparison = json.loads((capture / "comparison.json").read_text())
    acquisition = json.loads((capture / "acquisition.json").read_text())
    if comparison.get("status") != "PASS" or comparison.get("acquisition_sha256") != digest(capture / "acquisition.json"):
        raise ValueError("workload source must be an approved, unmodified live capture")
    if acquisition["artifacts_sha256"]["reference.bin"] != digest(capture / "reference.bin"):
        raise ValueError("GPS reference modified")
    bit_ns = 1e9 / 9600
    # The UART RX requires a complete idle bit after datapath reset before it
    # arms its start-bit detector. Three bit periods also cover synchronized
    # reset release and configuration; starting earlier can miss the first
    # byte and make a sound RTL design appear to fail the power-simulation
    # byte-exact gate.
    warmup_ns = round(3 * bit_ns)
    if kind == "idle":
        return b"", [], warmup_ns, warmup_ns + round(duration * 1e9)
    if kind == "saturated":
        character_ns = round(10 * bit_ns)
        analysis_start_ns = warmup_ns + character_ns
        count = math.ceil((analysis_start_ns - warmup_ns + round(duration * 1e9))
                          / character_ns) + 1
        payload, _ = make_payload(reference, count)
        edges = [warmup_ns + round(i * 10 * bit_ns) for i in range(count)]
        # Let one complete frame enter before measuring sustained traffic.
        return payload, edges, analysis_start_ns, analysis_start_ns + round(duration * 1e9)
    rate = acquisition["sample_rate_hz"]
    original = acquisition["reference_frame_start_samples"]
    if len(original) != len(reference) or rate / 9600 < 16:
        raise ValueError("missing reliable live timestamps")
    relative = [(s - original[0]) / rate for s in original]
    if relative[-1] < start + duration + 10 / 9600:
        raise ValueError("approved GPS trace too short for requested steady-state window")
    count = next(i for i, seconds in enumerate(relative) if seconds >= start + duration)
    edges = [warmup_ns + round(seconds * 1e9) for seconds in relative[:count]]
    # Sample quantization can make adjacent nominal frames overlap by <=1 sample.
    for i in range(1, len(edges)):
        minimum = edges[i - 1] + round(10 * bit_ns)
        if edges[i] < minimum:
            if minimum - edges[i] > math.ceil(1e9 / rate) + 2:
                raise ValueError("observed live frames overlap beyond sample quantization")
            edges[i] = minimum
    return reference[:count], edges, warmup_ns + round(start * 1e9), warmup_ns + round((start + duration) * 1e9)


def expected_output(build, payload, aes):
    if not aes:
        return payload
    # Only constants baked into this fitted netlist establish its oracle context.
    source = (build / "context_params.sv").read_text()
    values = []
    for name, bits in (("KEY", 128), ("NONCE", 96), ("COUNTER", 32)):
        match = re.search(rf"CONTEXT_{name}\s*=\s*{bits}'h([0-9a-fA-F]+)", source)
        if not match:
            raise ValueError("fitted context constants unavailable")
        values.append(int(match[1], 16))
    return crypt(values[0].to_bytes(16, "big"), values[1].to_bytes(12, "big"), values[2], payload)


def harness(top, count, finish_ns):
    return f'''`timescale 1ns/1ps
module tb;
  reg MAX10_CLK1_50=0, KEY0_N=0, UART_RX=1;
  wire UART_TX;
  wire [9:0] LEDR;
  reg [7:0] stimulus [0:{max(0, count - 1)}];
  reg [63:0] edges [0:{max(0, count - 1)}];
  integer i, j, out_file, received=0;
  reg [7:0] value;
  localparam real BIT_NS=1000000000.0/9600.0;
  {top} dut(.MAX10_CLK1_50(MAX10_CLK1_50), .KEY0_N(KEY0_N),
    .UART_RX(UART_RX), .UART_TX(UART_TX), .LEDR(LEDR));
  always #10 MAX10_CLK1_50=~MAX10_CLK1_50;
  initial begin
    out_file=$fopen("received.hex","w");
    #1000 KEY0_N=1;
  end
  initial begin
    if ({count}>0) begin
      $readmemh("stimulus.hex",stimulus);
      $readmemh("edges.hex",edges);
      for (i=0;i<{count};i=i+1) begin
        if (edges[i]>$realtime) #(edges[i]-$realtime);
        UART_RX=0; #(BIT_NS);
        for(j=0;j<8;j=j+1) begin UART_RX=stimulus[i][j]; #(BIT_NS); end
        UART_RX=1; #(BIT_NS);
      end
    end
  end
  initial begin
    wait(KEY0_N===1'b1);
    forever begin
      @(negedge UART_TX);
      #(BIT_NS/2);
      if (UART_TX!==1'b0) $fatal(1,"invalid UART start");
      for(integer b=0;b<8;b=b+1) begin
        #(BIT_NS);
        if (UART_TX!==1'b0 && UART_TX!==1'b1) $fatal(1,"unknown UART data");
        value[b]=UART_TX;
      end
      #(BIT_NS);
      if (UART_TX!==1'b1) $fatal(1,"invalid UART stop");
      $fdisplay(out_file,"%02x",value);
      received=received+1;
    end
  end
  initial begin
    #{finish_ns};
    if(received!={count}) $fatal(1,"incomplete output %0d expected {count}",received);
    if(LEDR[6]!==0 || LEDR[7]!==0) $fatal(1,"FPGA error flag");
    $fclose(out_file);
    $display("POSTFIT_FUNCTIONAL_PASS bytes=%0d",received);
    $finish;
  end
endmodule
'''


def simulation_do(vcd_path, begin_ns, duration_ns):
    """Capture one bounded VCD, stop dumping, then drain for functional checks."""
    return "\n".join((
        "onerror {quit -code 1}",
        "onbreak {quit -code 1}",
        "vsim -voptargs=+acc work.tb",
        f"run {begin_ns} ns",
        f"vcd file {tcl(vcd_path)}",
        # Do not descend into vendor primitive internals (especially the
        # uninitialized RAM-model state); preserve the post-fit design nets.
        "vcd add -r -nocell /tb/dut/implementation/*",
        "vcd add /tb/dut/MAX10_CLK1_50 /tb/dut/KEY0_N /tb/dut/UART_RX /tb/dut/UART_TX /tb/dut/LEDR",
        "vcd on",
        f"run {duration_ns} ns",
        "vcd flush",
        "vcd off",
        "run -all",
        "quit -code 0",
        "",
    ))


def trim_vcd_window(vcd_path, end_ns):
    """Crop post-window drain activity without emitting a VCD dumpoff/X event."""
    end_ps = round(end_ns * 1000)
    temporary = vcd_path.with_name(vcd_path.name + ".windowed")
    found_end = False
    with vcd_path.open("rb") as source, temporary.open("xb") as target:
        for line in source:
            if line.startswith(b"$dumpoff"):
                if not found_end:
                    raise ValueError("VCD dumping stopped before the requested window ended")
                break
            if line.startswith(b"#"):
                try:
                    stamp_ps = int(line[1:].strip())
                except ValueError as exc:
                    raise ValueError("malformed VCD timestamp") from exc
                if stamp_ps > end_ps:
                    break
                found_end = found_end or stamp_ps == end_ps
            target.write(line)
        if not found_end:
            target.write(f"#{end_ps}\n".encode("ascii"))
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, vcd_path)
    return end_ps


def validate_window(duration, segment_ms):
    if (not math.isfinite(duration) or duration <= 0 or
            segment_ms not in range(1, MAX_SEGMENT_MS + 1)):
        raise ValueError(f"finite positive duration; VCD segment must be 1..{MAX_SEGMENT_MS} ms")
    if duration * 1000 > segment_ms:
        raise ValueError(f"one VCD segment is limited to {MAX_SEGMENT_MS} ms")


def simulate(args):
    validate_window(args.duration, args.segment_ms)
    if args.temperature not in (25, 50, 70) or args.load_pf not in (5, 10, 15):
        raise ValueError("unsupported comparison conditions")
    if shutil.disk_usage(ROOT).free < 2 * 1024**3:
        raise ValueError("at least 2 GiB free required for bounded VCD segments")
    vsim = args.vsim.resolve()
    for name in ("vsim", "vlog", "vlib"):
        if not vsim.with_name(name).is_file():
            raise ValueError(f"Questa {name} unavailable; install official licensed Starter Edition")
    metadata = json.loads((args.prepared / "preparation.json").read_text())
    build_info = metadata["builds"][args.mode]
    original = Path(build_info["original"])
    verify(original)
    clone = (args.prepared / args.mode).resolve()
    netlist = clone / "netlist" / (build_info["project"] + ".vo")
    if digest(netlist) != build_info["netlist_sha256"]:
        raise ValueError("post-fit netlist modified")
    payload, edges, begin_ns, end_ns = workload(args.capture, args.workload, args.window_start, args.duration)
    expected = expected_output(original, payload, args.mode == "aes-ctr")
    bit_ns = 1e9 / 9600
    # Leave margin for RX completion, FIFO/AES scheduling, and the entire TX
    # frame after the final input byte; dumping is already off at end_ns.
    finish_ns = max(end_ns, (edges[-1] + round(30 * bit_ns)) if edges else end_ns) + 1000
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "build/power-analysis"):
        raise ValueError("simulation output must be new and below build/power-analysis")
    output.mkdir(parents=True, exist_ok=False)
    (output / "stimulus.hex").write_text("\n".join(f"{v:02x}" for v in payload) + "\n")
    (output / "edges.hex").write_text("\n".join(f"{v:016x}" for v in edges) + "\n")
    (output / "tb.sv").write_text(harness(build_info["top"], len(payload), finish_ns))
    library = args.quartus_bin.resolve().parent / "eda/sim_lib"
    files = [library / name for name in ("altera_primitives.v", "220model.v", "sgate.v",
        "altera_mf.v", "altera_lnsim.sv", "mentor/fiftyfivenm_atoms_ncrypt.v", "fiftyfivenm_atoms.v")]
    if any(not p.is_file() for p in files):
        raise ValueError("official MAX 10 simulation libraries unavailable")
    run([vsim.with_name("vlib"), "work"], output, output / "vlib.log")
    run([vsim.with_name("vlog"), "-sv", *files, netlist, output / "tb.sv"], output, output / "vlog.log")
    run([args.quartus_bin / "quartus_sh", "-t", clone / "conditions.tcl",
         args.temperature, args.load_pf], clone, output / "conditions.log")
    interval = end_ns - begin_ns
    vcd = output / "segment-000.vcd"
    destination = output / "segment-000"
    (output / "simulate.do").write_text(simulation_do(vcd, begin_ns, interval))
    run([vsim, "-c", "-do", "simulate.do"], output, output / "vsim.log")
    if "POSTFIT_FUNCTIONAL_PASS" not in (output / "vsim.log").read_text():
        raise ValueError("post-fit output check did not complete")
    trim_vcd_window(vcd, end_ns)
    received = bytes.fromhex((output / "received.hex").read_text())
    if received != expected:
        raise ValueError("post-fit output differs from independent AES/UART oracle")
    power = segment(clone, vcd, destination, args.quartus_bin)
    segments = [json.loads((destination / "segment.json").read_text())]
    means = {field: power[field] for field in ("total_mw", "dynamic_mw", "static_mw", "io_mw")}
    result = {"status": "SIMULATED_ESTIMATE_PENDING_REVIEW", "publishable": False,
        "mode": args.mode, "workload": args.workload, "duration_seconds": args.duration,
        "window_start_seconds": args.window_start, "bytes_verified": len(payload),
        "activity_window_ns": {"start": begin_ns, "end": end_ns, "finish_check": finish_ns},
        "weighted_mean_mw": means, "byte_exact": True, "postfit_functional_simulation": True,
        "clock_io_mapping_verified": False, "doubling_dynamic_change_percent": None,
        "conditions": {"junction_celsius": args.temperature, "uart_tx_load_pf": args.load_pf},
        "source_manifest_sha256": digest(original / "build-manifest.json"),
        "gps_reference_sha256": digest(args.capture / "reference.bin"),
        "segments": segments, "note": "Review all segments and duration convergence before publication."}
    (output / "simulation.json").write_text(json.dumps(result, indent=2) + "\n")
    verify(original)
    return {"status": result["status"], "output": str(output), "bytes_verified": len(payload)}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--mode", choices=("baseline", "aes-ctr"), required=True)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--workload", choices=("idle", "live", "saturated"), required=True)
    p.add_argument("--window-start", type=float, default=0)
    p.add_argument("--duration", type=float, default=0.001)
    p.add_argument("--segment-ms", type=int, choices=range(1, MAX_SEGMENT_MS + 1),
                   default=MAX_SEGMENT_MS)
    p.add_argument("--temperature", type=int, default=25)
    p.add_argument("--load-pf", type=int, default=10)
    p.add_argument("--vsim", type=Path, required=True)
    quartus_sh = shutil.which("quartus_sh")
    quartus_bin = Path(quartus_sh).resolve().parent if quartus_sh else None
    p.add_argument("--quartus-bin", type=Path, default=quartus_bin,
                   required=quartus_bin is None)
    p.add_argument("--output", type=Path, required=True)
    try:
        print(json.dumps(simulate(p.parse_args()), indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL post-fit simulation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
