#!/usr/bin/env python3
"""Compile a fresh bench context without replacing the article's selected fits."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from build_manifest import ROOT, begin, digest, finish, verify
from context import render_context_sv, validate_context


def project_text(source, output):
    def resolve(match):
        prefix, name = match.groups()
        path = (source.parent / name.strip('"')).resolve()
        if path.name == "context_params.sv":
            path = output / path.name
        if not path.is_file():
            raise ValueError(f"missing project input: {path}")
        return prefix + '"' + str(path) + '"'
    text = re.sub(r"^(set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|SDC)_FILE\s+)(.+)$",
                  resolve, source.read_text(), flags=re.M)
    return re.sub(r"^set_global_assignment -name PROJECT_OUTPUT_DIRECTORY .+$",
                  f'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY "{output}"', text, flags=re.M)


def build(context_file, output, quartus_sh, prepare_only=False):
    context = json.loads(context_file.read_text())
    mode, *_ = validate_context(context)
    design = "secure" if mode == "aes-128-ctr" else "baseline"
    output = output.resolve()
    if not output.is_relative_to(ROOT / "build/experiments"):
        raise ValueError("output must be a NEW directory below build/experiments")
    source = ROOT / "fpga/de10_lite" / design / f"uart_{design}.qsf"
    output.mkdir(parents=True, exist_ok=False)
    render_context_sv(context_file, output / "context_params.sv", mode)
    qsf = output / source.name
    qsf.write_text(project_text(source, output))
    shutil.copyfile(source.with_suffix(".qpf"), qsf.with_suffix(".qpf"))
    begin(qsf, output, "de10_lite", design)
    binding = {"schema": 1, "context_id": context["context_id"],
               "context_sha256": digest(context_file), "mode": mode, "bytes": context["bytes"],
               "note": "New experiment build, not the selected publication fit. Not programmed."}
    (output / "context-binding.json").write_text(json.dumps(binding, indent=2) + "\n")
    if prepare_only:
        return {"status": "PREPARED", "project": str(qsf)}
    for exe in (quartus_sh, quartus_sh.with_name("quartus_sta")):
        if not exe.is_file():
            raise ValueError(f"Quartus executable missing: {exe}")
    commands = (([quartus_sh, "--flow", "compile", qsf.stem], "compile.log"),
                ([quartus_sh.with_name("quartus_sta"), "-t", ROOT / "scripts/quartus_timing.tcl",
                  qsf.stem, output], "timing-audit.log"),
                ([quartus_sh, "--version"], "tool-version.txt"))
    for command, log in commands:
        print(f"BUILD {design}: {log}", flush=True)
        with (output / log).open("x") as stream:
            result = subprocess.run(list(map(str, command)), cwd=output, stdout=stream, stderr=subprocess.STDOUT)
        content = (output / log).read_text()
        if result.returncode or re.search(r"^(?:Error|Critical Warning)\b", content, re.M):
            raise ValueError(f"Quartus failed; inspect {output / log}")
    if "PASS: 3 timing corners audited" not in (output / "timing-audit.log").read_text():
        raise ValueError("timing audit did not pass")
    finish(output)
    verify(output)
    return {"status": "PASS", "sof": str(output / f"uart_{design}.sof"),
            "context_id": context["context_id"], "note": "Generated and audited, NOT programmed"}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--context", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--quartus-sh", type=Path, default=Path(shutil.which("quartus_sh") or
        "/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_sh"))
    a = p.parse_args()
    try:
        print(json.dumps(build(a.context, a.output, a.quartus_sh, a.prepare_only), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL isolated bench build: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
