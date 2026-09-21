#!/usr/bin/env python3
"""Extract comparable DE10-Lite baseline/secure metrics from Quartus reports."""
import argparse
import json
import math
import re
from pathlib import Path
from build_manifest import verify as verify_manifest


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUILD = ROOT / "build/de10_lite"

FIT_FIELDS = {
    "logic_elements": r"Total logic elements\s*:\s*([\d,]+)",
    "registers": r"Total registers\s*:\s*([\d,]+)",
    "memory_bits": r"Total memory bits\s*:\s*([\d,]+)",
    "pins": r"Total pins\s*:\s*([\d,]+)",
    "plls": r"Total PLLs\s*:\s*([\d,]+)",
    "device": r"Device\s*:\s*(\S+)",
    "quartus_version": r"Quartus Prime Version\s*:\s*(.+)",
}
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
SLACK_RE = re.compile(rf"AUDIT corner=(\d+) check=(\w+) slack_ns=({NUMBER})")
FMAX_RE = re.compile(rf";\s*({NUMBER}) MHz\s*;\s*({NUMBER}) MHz\s*;")
BUILD_PASS = "PASS: Quartus compilation and timing audit; SOF generated, not programmed"


def _number(value: str) -> int:
    return int(value.replace(",", ""))


def _fit_metrics(path: Path) -> dict[str, object]:
    reports = sorted(path.glob("*.fit.summary"))
    if len(reports) != 1:
        raise ValueError(f"{path}: expected one *.fit.summary, found {len(reports)}")
    text = reports[0].read_text(encoding="utf-8", errors="replace")
    if not re.search(r"^Fitter Status\s*:\s*Successful\b", text, re.M):
        raise ValueError(f"{reports[0]}: fitter did not succeed")
    result: dict[str, object] = {}
    for name, expression in FIT_FIELDS.items():
        match = re.search(expression, text)
        if not match:
            raise ValueError(f"{reports[0]}: missing {name}")
        result[name] = _number(match.group(1)) if name not in {"device", "quartus_version"} else match.group(1).strip()
    return result


def _timing_metrics(path: Path) -> dict[str, object]:
    fmax_by_corner = {}
    for report in sorted(path.glob("fmax_corner*.rpt")):
        name = re.fullmatch(r"fmax_corner([1-9]\d*)\.rpt", report.name)
        rows = FMAX_RE.findall(report.read_text(encoding="utf-8", errors="replace"))
        if not name or len(rows) != 1:
            raise ValueError(f"{report}: expected one valid Fmax row and corner")
        values = [float(value) for value in rows[0]]
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError(f"{report}: invalid Fmax")
        fmax_by_corner[int(name.group(1))] = values[0]
    if not fmax_by_corner:
        raise ValueError(f"{path}: no fmax_corner*.rpt reports")

    audit = path / "timing-audit.log"
    contents = audit.read_text(encoding="utf-8", errors="replace")
    final = re.findall(r"^PASS: ([1-9]\d*) timing corners audited$", contents, re.M)
    if len(final) != 1 or re.search(r"^Error\b|^FAIL\b", contents, re.M):
        raise ValueError(f"{audit}: timing audit did not succeed")
    corners = set(range(1, int(final[0]) + 1))
    if set(fmax_by_corner) != corners:
        raise ValueError(f"{audit}: Fmax/timing corner mismatch")
    checks = {}
    for line in contents.splitlines():
        if not line.startswith("AUDIT"):
            continue
        match = SLACK_RE.fullmatch(line)
        if not match:
            raise ValueError(f"{audit}: malformed or failed AUDIT record")
        corner, check, raw = match.groups()
        key = (int(corner), check)
        value = float(raw)
        if key in checks or not math.isfinite(value) or value < 0:
            raise ValueError(f"{audit}: duplicate, non-finite or negative slack: {line}")
        checks[key] = value
    required = {"setup", "hold", "recovery", "removal"}
    if set(checks) != {(corner, check) for corner in corners for check in required}:
        raise ValueError(f"{audit}: missing/extra per-corner checks")
    fmax_values = [fmax_by_corner[corner] for corner in sorted(corners)]
    return {
        "fmax_mhz_by_corner": fmax_values,
        "fmax_mhz_min": min(fmax_values),
        "slack_ns_min": {check: min(checks[(corner, check)] for corner in corners) for check in sorted(required)},
    }


def collect(build_root: Path = DEFAULT_BUILD, source_root: Path = ROOT) -> dict[str, object]:
    result: dict[str, object] = {"build_root": str(build_root), "designs": {}}
    for design in ("baseline", "secure"):
        path = build_root / design
        if not path.is_dir():
            raise ValueError(f"missing build directory: {path}")
        if (path / "build-status.txt").read_text().strip() != BUILD_PASS:
            raise ValueError(f"{path}: build did not pass")
        provenance = verify_manifest(path, source_root=source_root)
        if provenance["board"] != "de10_lite" or provenance["design"] != design:
            raise ValueError(f"{path}: wrong build target in manifest")
        metrics = _fit_metrics(path)
        metrics.update(_timing_metrics(path))
        if metrics["device"] != provenance["device"]:
            raise ValueError(f"{path}: report/manifest device mismatch")
        metrics["provenance"] = provenance
        result["designs"][design] = metrics

    baseline = result["designs"]["baseline"]
    secure = result["designs"]["secure"]
    for field in ("device", "quartus_version", "memory_bits", "pins", "plls"):
        if baseline[field] != secure[field]:
            raise ValueError(f"baseline/secure configuration mismatch: {field}")
    for field in ("seed", "clock_hz", "baud", "fifo_depth", "shared_rtl_sha256"):
        if baseline["provenance"][field] != secure["provenance"][field]:
            raise ValueError(f"baseline/secure provenance mismatch: {field}")
    if not baseline["logic_elements"] or not baseline["registers"]:
        raise ValueError("baseline resource counts must be nonzero")
    result["comparison"] = {
        "logic_elements_delta": secure["logic_elements"] - baseline["logic_elements"],
        "logic_elements_delta_pct": (secure["logic_elements"] / baseline["logic_elements"] - 1) * 100,
        "registers_delta": secure["registers"] - baseline["registers"],
        "registers_delta_pct": (secure["registers"] / baseline["registers"] - 1) * 100,
        "fmax_delta_mhz": secure["fmax_mhz_min"] - baseline["fmax_mhz_min"],
        "fmax_delta_pct": (secure["fmax_mhz_min"] / baseline["fmax_mhz_min"] - 1) * 100,
    }
    return result


def markdown(result: dict[str, object]) -> str:
    designs = result["designs"]
    comparison = result["comparison"]
    lines = [
        "# Métricas FPGA — DE10-Lite",
        "",
        "Relatórios pós-fit aprovados, com cobertura temporal completa e hashes conferidos; não são medições de bancada.",
        "",
        "| Métrica | Baseline | Secure |",
        "| --- | ---: | ---: |",
        f"| Logic elements | {designs['baseline']['logic_elements']:,} | {designs['secure']['logic_elements']:,} |",
        f"| Registradores | {designs['baseline']['registers']:,} | {designs['secure']['registers']:,} |",
        f"| Memória (bits) | {designs['baseline']['memory_bits']:,} | {designs['secure']['memory_bits']:,} |",
        f"| Fmax mínima (MHz) | {designs['baseline']['fmax_mhz_min']:.2f} | {designs['secure']['fmax_mhz_min']:.2f} |",
        f"| Pior setup (ns) | {designs['baseline']['slack_ns_min']['setup']:.3f} | {designs['secure']['slack_ns_min']['setup']:.3f} |",
        f"| Pior hold (ns) | {designs['baseline']['slack_ns_min']['hold']:.3f} | {designs['secure']['slack_ns_min']['hold']:.3f} |",
        f"| Pior recovery (ns) | {designs['baseline']['slack_ns_min']['recovery']:.3f} | {designs['secure']['slack_ns_min']['recovery']:.3f} |",
        f"| Pior removal (ns) | {designs['baseline']['slack_ns_min']['removal']:.3f} | {designs['secure']['slack_ns_min']['removal']:.3f} |",
        "",
        "## Acréscimo do secure",
        "",
        f"- Logic elements: +{comparison['logic_elements_delta']:,} ({comparison['logic_elements_delta_pct']:.2f}%).",
        f"- Registradores: +{comparison['registers_delta']:,} ({comparison['registers_delta_pct']:.2f}%).",
        f"- Fmax: {comparison['fmax_delta_mhz']:.2f} MHz ({comparison['fmax_delta_pct']:.2f}%).",
        "",
        "O clock de operação continua sendo 50 MHz nos dois projetos; Fmax é a margem estimada pelo Quartus.",
        "O JSON acompanha revisão, estado das fontes, seed e hashes de entradas/artefatos de cada build.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    result = collect(args.build_root.resolve())
    serialized = json.dumps(result, indent=2) + "\n"
    if args.json:
        args.json.write_text(serialized, encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown(result), encoding="utf-8")
    if not args.json and not args.markdown:
        print(serialized, end="")
    else:
        print("PASS FPGA metrics: baseline/secure Quartus reports parsed")


if __name__ == "__main__":
    main()
