#!/usr/bin/env python3
"""Check that manuscript drafts retain current results and evidence limits."""
import argparse
import json
import math
from pathlib import Path
import re
import sys

from build_manifest import digest
from fpga_metrics import DEFAULT_BUILD, collect, comparison, comparison_table, number


ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "docs/evidence/de10-lite-postfit-2026-09-30.json"

REQUIREMENTS = {
    "English": (
        ROOT / "docs/manuscrito-btsym-draft.md",
        (
            "50 MHz",
            "38400 baud",
            "309 bytes",
            "synthetic replay",
            "physical",
            "NEO-M8N",
            "P07",
            "P13",
            "8,192 bytes",
            "127 complete NMEA sentences",
            "32,768-byte",
            "live GPS-to-AES-CTR path",
            "parallel raw GPS input",
        ),
    ),
    "Portuguese": (
        ROOT / "docs/manuscrito-btsym-rascunho-pt.md",
        (
            "50 MHz",
            "38400 baud",
            "309 bytes",
            "replay NMEA público",
            "físic",
            "NEO-M8N",
            "P07",
            "P13",
            "8.192 bytes",
            "127 sentenças NMEA",
            "32.768 bytes",
            "GPS→AES-CTR ao vivo",
            "entrada GPS crua",
        ),
    ),
}


def load_metrics(path: Path, source_root: Path = ROOT) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("schema") != 1:
        raise ValueError("unsupported publication snapshot")
    result = snapshot["results"]
    if result["board"] != "de10_lite" or set(result["designs"]) != {"baseline", "secure"}:
        raise ValueError("publication snapshot must select the DE10-Lite pair")
    for name, design in result["designs"].items():
        for field in ("logic_elements", "registers", "memory_bits", "pins", "plls"):
            value = design[field]
            if type(value) is not int or value < 0 or (field in ("logic_elements", "registers") and not value):
                raise ValueError(f"{name}: invalid {field}")
        for field in ("fmax_mhz_min", "restricted_fmax_mhz_min"):
            values = design[field.replace("_min", "_by_corner")]
            if len(values) != 3 or any(not math.isfinite(v) or v <= 0 for v in values):
                raise ValueError(f"{name}: invalid timing corners")
            if design[field] != min(values):
                raise ValueError(f"{name}: inconsistent {field}")
        if set(design["slack_ns_min"]) != {"setup", "hold", "recovery", "removal"}:
            raise ValueError(f"{name}: missing timing checks")
        if any(not math.isfinite(v) or v < 0 for v in design["slack_ns_min"].values()):
            raise ValueError(f"{name}: invalid timing slack")
        provenance = design["provenance"]
        if (provenance["schema"] != 1 or provenance["status"] != "PASS"
                or provenance["design"] != name or provenance["board"] != result["board"]
                or provenance["device"] != design["device"]):
            raise ValueError(f"{name}: invalid build provenance")
        if not provenance["sources_sha256"] or not provenance["artifacts_sha256"]:
            raise ValueError(f"{name}: missing provenance hashes")
        for hashes in (provenance["sources_sha256"], provenance["artifacts_sha256"]):
            if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values()):
                raise ValueError(f"{name}: invalid provenance hash")
        if design["restricted_fmax_mhz_min"] < provenance["clock_hz"] / 1_000_000:
            raise ValueError(f"{name}: operating clock not met")
        for source, expected in provenance["sources_sha256"].items():
            current = (source_root / source).resolve()
            if not current.is_relative_to(source_root.resolve()):
                raise ValueError("source path escapes repository")
            # The generated context package is deliberately private and absent
            # in a fresh clone. Its hash remains bound to the selected SOF.
            if source.startswith("build/"):
                continue
            if not current.is_file() or digest(current) != expected:
                raise ValueError(f"{name}: published build source changed: {source}")
    b, s = (result["designs"][name] for name in ("baseline", "secure"))
    for field in ("device", "quartus_version", "memory_bits", "pins", "plls"):
        if b[field] != s[field]:
            raise ValueError(f"publication pair mismatch: {field}")
    for field in ("board", "device", "seed", "clock_hz", "baud", "fifo_depth", "shared_rtl_sha256"):
        if b["provenance"][field] != s["provenance"][field]:
            raise ValueError(f"publication provenance mismatch: {field}")
    if result["comparison"] != comparison(result["designs"]):
        raise ValueError("publication deltas do not match selected builds")
    return result


def check_builds(result: dict, build_root: Path = DEFAULT_BUILD) -> bool:
    present = [(build_root / name).exists() for name in ("baseline", "secure")]
    if not any(present):
        return False
    if not all(present):
        raise ValueError("incomplete local baseline/secure build pair")
    current = collect(build_root)
    if current["designs"] != result["designs"] or current["comparison"] != result["comparison"]:
        raise ValueError("local builds differ from publication snapshot; select and review a new pair")
    return True


def check_draft(label: str, path: Path, markers: tuple[str, ...], metrics: dict) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
        text = " ".join(raw.split())
    except OSError as exc:
        return [f"{label}: cannot read {path}: {exc}"]
    normalized_markers = [" ".join(marker.split()) for marker in markers]
    missing = [marker for marker in normalized_markers if marker not in text]
    failures = [f"{label}: missing required disclosure/result: {marker!r}" for marker in missing]
    # Compare rows, including deltas and every audited slack, rather than finding
    # unrelated numbers elsewhere in the manuscript.
    normalize = lambda row: tuple(cell.strip() for cell in row.strip().strip("|").split("|"))
    actual_rows = [normalize(line) for line in raw.splitlines() if line.lstrip().startswith("|")]
    for row in comparison_table(metrics, label).splitlines()[2:]:
        expected = normalize(row)
        matching = [actual for actual in actual_rows if actual[0] == expected[0]]
        if matching != [expected]:
            failures.append(f"{label}: post-fit row differs from selected build: {expected[0]}")
    heading = "Abstract" if label == "English" else "Resumo"
    abstract = re.search(rf"^## {heading}\s*\n(.*?)(?=^## |\Z)", raw, re.M | re.S)
    if not abstract:
        failures.append(f"{label}: missing abstract")
    else:
        for design in metrics["designs"].values():
            for token in (number(design["logic_elements"], label), number(design["registers"], label),
                          number(design["fmax_mhz_min"], label, 2)):
                if not re.search(rf"(?<![\d.,]){re.escape(token)}(?![\d.,])", abstract[1]):
                    failures.append(f"{label}: abstract differs from selected build: {token}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--offline", action="store_true", help="Check the published snapshot and tracked sources only")
    args = parser.parse_args()
    try:
        metrics = load_metrics(args.snapshot)
        live = not args.offline and check_builds(metrics, args.build_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL manuscript provenance: {exc}", file=sys.stderr)
        return 1
    failures = []
    for label, (path, markers) in REQUIREMENTS.items():
        draft_failures = check_draft(label, path, markers, metrics)
        failures.extend(draft_failures)
        if not draft_failures:
            print(f"PASS manuscript check: {label} draft")
    if failures:
        for failure in failures:
            print(f"FAIL manuscript check: {failure}", file=sys.stderr)
        return 1
    print("PASS manuscript provenance: selected snapshot and tracked build sources verified")
    print("PASS local build hashes match publication snapshot" if live else
          "INFO: local artifacts not checked; this run verifies the published snapshot only")
    print("PASS manuscript check: post-fit tables and abstracts match the selected builds; evidence disclosures present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
