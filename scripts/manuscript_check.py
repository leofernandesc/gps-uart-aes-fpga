#!/usr/bin/env python3
"""Check the submitted manuscript source against the selected evidence."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import subprocess

from build_manifest import digest
from fpga_metrics import collect, comparison, number


ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "docs/evidence/de10-lite-postfit-9600-2026-09-30.json"
SELECTED_BUILD = ROOT / "build/experiments/baud9600"

PAPER_SOURCE = ROOT / "paper/main.tex"
SUBMITTED_PDF = ROOT / "paper/submitted.pdf"
SUBMITTED_HASH = ROOT / "paper/submitted.sha256"
PAPER_MARKERS = (
    r"\title{Hardware Cost and Live GPS Data-Path Evaluation of AES-128-CTR on an FPGA}",
    "9600/8N1",
    "1,024-byte FIFO",
    "65,536-byte AES-CTR trial",
    "1,112 complete checksum-valid NMEA sentences",
    "Declaration of AI-assisted technologies.",
    "OpenAI ChatGPT and Codex",
    "The authors declare that they have no competing interests.",
)


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
    if (b["provenance"]["baud"] != 9600 or b["provenance"]["clock_hz"] != 50_000_000
            or b["provenance"]["fifo_depth"] != 1024):
        raise ValueError("publication snapshot is not the selected 50 MHz/9600/1024-byte profile")
    for field in ("device", "quartus_version", "memory_bits", "pins", "plls"):
        if b[field] != s[field]:
            raise ValueError(f"publication pair mismatch: {field}")
    for field in ("board", "device", "seed", "clock_hz", "baud", "fifo_depth", "shared_rtl_sha256"):
        if b["provenance"][field] != s["provenance"][field]:
            raise ValueError(f"publication provenance mismatch: {field}")
    if result["comparison"] != comparison(result["designs"]):
        raise ValueError("publication deltas do not match selected builds")
    return result


def check_builds(result: dict, build_root: Path = SELECTED_BUILD) -> bool:
    present = [(build_root / name).exists() for name in ("baseline", "secure")]
    if not any(present):
        return False
    if not all(present):
        raise ValueError("incomplete local baseline/secure build pair")
    current = collect(build_root)
    if current["designs"] != result["designs"] or current["comparison"] != result["comparison"]:
        raise ValueError("local builds differ from publication snapshot; select and review a new pair")
    return True


def render_metrics(result: dict) -> str:
    designs = result["designs"]
    values = (
        ("BaselineLE", str(designs["baseline"]["logic_elements"])),
        ("BaselineReg", str(designs["baseline"]["registers"])),
        ("BaselineFmax", f'{designs["baseline"]["fmax_mhz_min"]:.2f}'),
        ("SecureLE", str(designs["secure"]["logic_elements"])),
        ("SecureReg", str(designs["secure"]["registers"])),
        ("SecureFmax", f'{designs["secure"]["fmax_mhz_min"]:.2f}'),
    )
    return "".join(f"\\newcommand{{\\{name}}}{{{value}}}\n" for name, value in values)


def check_paper(metrics: dict) -> list[str]:
    failures = []
    try:
        source = PAPER_SOURCE.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read submitted manuscript source: {exc}"]

    normalized = " ".join(source.split())
    for marker in PAPER_MARKERS:
        if marker not in normalized:
            failures.append(f"submitted manuscript is missing required content: {marker!r}")

    rendered_metrics = render_metrics(metrics)
    expected_macros = dict(re.findall(
        r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", rendered_metrics))
    source_macros = dict(re.findall(
        r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", source))
    for name, value in expected_macros.items():
        if source_macros.get(name) != value:
            failures.append(f"submitted manuscript metric macro differs from selected snapshot: {name}")
    try:
        if (ROOT / "paper/generated_metrics.tex").read_text(encoding="utf-8") != rendered_metrics:
            failures.append("generated manuscript metrics differ from selected snapshot")
    except OSError as exc:
        failures.append(f"cannot read generated manuscript metrics: {exc}")
    for macro in (r"\BaselineLE{}", r"\BaselineReg{}", r"\BaselineFmax{}",
                  r"\SecureLEPrint{}", r"\SecureReg{}", r"\SecureFmax{}"):
        if macro not in source:
            failures.append(f"submitted manuscript does not use selected metric macro {macro}")

    result = metrics
    comparison_result = result["comparison"]
    for number_text in (
        f"+{comparison_result['logic_elements_delta']:,}",
        f"+{comparison_result['registers_delta']:,}",
        f"{comparison_result['fmax_delta_mhz']:.2f}",
        f"{result['designs']['baseline']['fmax_mhz_min']:.2f}",
        f"{result['designs']['secure']['fmax_mhz_min']:.2f}",
    ):
        if number_text not in source:
            failures.append(f"submitted manuscript does not contain selected result {number_text}")

    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.S)
    if not abstract:
        failures.append("submitted manuscript has no abstract")
    else:
        words = re.findall(r"\b[\w-]+\b", re.sub(r"\\[a-zA-Z]+", " ", abstract[1]))
        if not 150 <= len(words) <= 250:
            failures.append(f"abstract has {len(words)} words; expected 150--250")
        expanded_abstract = abstract[1]
        for name, value in source_macros.items():
            expanded_abstract = expanded_abstract.replace(f"\\{name}{{}}", value)
        for design in result["designs"].values():
            for value in (number(design["logic_elements"], "English"),
                          number(design["registers"], "English"),
                          number(design["fmax_mhz_min"], "English", 2)):
                if not re.search(rf"(?<![\d.,]){re.escape(value)}(?![\d.,])", expanded_abstract):
                    failures.append(f"abstract differs from selected build: {value}")

    try:
        hashes = {}
        for line in SUBMITTED_HASH.read_text(encoding="ascii").splitlines():
            fields = line.split()
            if len(fields) == 2:
                hashes[fields[1].lstrip("*")] = fields[0]
        for name in ("main.tex", "submitted.pdf"):
            path = ROOT / "paper" / name
            if hashes.get(name) != digest(path):
                failures.append(f"archived submitted {name} does not match paper/submitted.sha256")
        info = subprocess.run(["pdfinfo", str(SUBMITTED_PDF)], check=True,
                              capture_output=True, text=True).stdout
        pages = re.search(r"^Pages:\s+(\d+)$", info, re.M)
        if not pages or int(pages[1]) > 10:
            failures.append("archived submitted PDF exceeds the 10-page limit or is unreadable")
    except (OSError, subprocess.CalledProcessError, IndexError) as exc:
        failures.append(f"cannot verify archived submitted PDF: {exc}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--build-root", type=Path, default=SELECTED_BUILD)
    parser.add_argument("--offline", action="store_true", help="Check the published snapshot and tracked sources only")
    args = parser.parse_args()
    try:
        metrics = load_metrics(args.snapshot)
        live = not args.offline and check_builds(metrics, args.build_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL manuscript provenance: {exc}", file=sys.stderr)
        return 1
    failures = check_paper(metrics)
    if failures:
        for failure in failures:
            print(f"FAIL manuscript check: {failure}", file=sys.stderr)
        return 1
    print("PASS manuscript provenance: selected snapshot and tracked build sources verified")
    print("PASS local build hashes match publication snapshot" if live else
          "INFO: local artifacts not checked; this run verifies the published snapshot only")
    print("PASS manuscript check: submitted source, selected metrics, PDF hash, page limit, and disclosures verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
