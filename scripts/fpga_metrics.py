#!/usr/bin/env python3
"""Extract comparable DE10-Lite baseline/secure metrics from Quartus reports."""
import argparse
import json
import re
from pathlib import Path


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
SLACK_RE = re.compile(r"AUDIT corner=(\d+) check=(\w+) slack_ns=([\d.]+)")
FMAX_RE = re.compile(r";\s*([\d.]+) MHz\s*;\s*([\d.]+) MHz\s*;")


def _number(value: str) -> int:
    return int(value.replace(",", ""))


def _fit_metrics(path: Path) -> dict[str, object]:
    reports = sorted(path.glob("*.fit.summary"))
    if len(reports) != 1:
        raise ValueError(f"{path}: expected one *.fit.summary, found {len(reports)}")
    text = reports[0].read_text(encoding="utf-8", errors="replace")
    result: dict[str, object] = {}
    for name, expression in FIT_FIELDS.items():
        match = re.search(expression, text)
        if not match:
            raise ValueError(f"{reports[0]}: missing {name}")
        result[name] = _number(match.group(1)) if name not in {"device", "quartus_version"} else match.group(1).strip()
    return result


def _timing_metrics(path: Path) -> dict[str, object]:
    fmax_values = []
    for report in sorted(path.glob("fmax_corner*.rpt")):
        match = FMAX_RE.search(report.read_text(encoding="utf-8", errors="replace"))
        if not match:
            raise ValueError(f"{report}: missing Fmax row")
        fmax_values.append(float(match.group(1)))
    if not fmax_values:
        raise ValueError(f"{path}: no fmax_corner*.rpt reports")

    audit = path / "timing-audit.log"
    checks: dict[str, list[float]] = {}
    for corner, check, value in SLACK_RE.findall(audit.read_text(encoding="utf-8", errors="replace")):
        checks.setdefault(check, []).append(float(value))
    required = {"setup", "hold", "recovery", "removal"}
    if set(checks) != required:
        raise ValueError(f"{audit}: expected {sorted(required)}, found {sorted(checks)}")
    return {
        "fmax_mhz_by_corner": fmax_values,
        "fmax_mhz_min": min(fmax_values),
        "slack_ns_min": {check: min(values) for check, values in checks.items()},
    }


def collect(build_root: Path = DEFAULT_BUILD) -> dict[str, object]:
    result: dict[str, object] = {"build_root": str(build_root), "designs": {}}
    for design in ("baseline", "secure"):
        path = build_root / design
        if not path.is_dir():
            raise ValueError(f"missing build directory: {path}")
        metrics = _fit_metrics(path)
        metrics.update(_timing_metrics(path))
        result["designs"][design] = metrics

    baseline = result["designs"]["baseline"]
    secure = result["designs"]["secure"]
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
        "Dados extraídos automaticamente dos relatórios pós-fit do Quartus; não são medições de bancada.",
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
