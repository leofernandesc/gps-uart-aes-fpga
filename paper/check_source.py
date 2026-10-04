#!/usr/bin/env python3
"""Check LaTeX source, citation keys, and frozen post-fit numeric macros."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

from build_metrics import render
from manuscript_check import SNAPSHOT


ROOT = Path(__file__).resolve().parent.parent


def check(paper=ROOT / "paper/main.tex", bibliography=ROOT / "paper/references.bib",
          macros=ROOT / "paper/generated_metrics.tex", pdf=None):
    source = paper.read_text(encoding="utf-8")
    expected_macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", render(SNAPSHOT)))
    if r"\input{generated_metrics.tex}" in source:
        if macros.read_text(encoding="utf-8") != render(SNAPSHOT):
            raise ValueError("paper macros differ from frozen post-fit snapshot")
    else:
        source_macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", source))
        mismatched = [name for name, value in expected_macros.items()
                      if source_macros.get(name) != value]
        if mismatched:
            raise ValueError("paper inline metrics differ from frozen post-fit snapshot: "
                             + ", ".join(mismatched))
    if (r"\bibliographystyle{splncs04}" not in source
            and r"\begin{thebibliography}" not in source):
        raise ValueError("paper must use an LNCS bibliography")
    cited = {key.strip() for group in re.findall(r"\\cite(?:\[[^]]*\])?\{([^}]+)\}", source)
             for key in group.split(",")}
    if r"\bibliography{" in source:
        bib = bibliography.read_text(encoding="utf-8")
        available = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib))
    else:
        available = set(re.findall(r"\\bibitem(?:\[[^]]*\])?\s*\{([^}]+)\}", source))
    missing, unused = cited - available, available - cited
    if missing:
        raise ValueError("undefined bibliography keys: " + ", ".join(sorted(missing)))
    if unused:
        raise ValueError("uncited bibliography entries: " + ", ".join(sorted(unused)))
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.S)
    if not abstract:
        raise ValueError("missing abstract")
    words = re.findall(r"\b[\w-]+\b", re.sub(r"\\[a-zA-Z]+", " ", abstract[1]))
    if not 150 <= len(words) <= 250:
        raise ValueError(f"abstract has {len(words)} words; Springer template requests 150--250")
    if "5603" in source or "103.38" in source:
        raise ValueError("historical, unselected post-fit numbers occur in paper source")
    placeholders = [token for token in ("Funding and acknowledgement statement to be confirmed",
        "Declaration to be confirmed by all authors")
        if token in source]
    result = {"source_check": "PASS", "abstract_words": len(words),
              "citations": sorted(cited), "submission_placeholders": placeholders}
    if pdf:
        if not pdf.is_file():
            raise ValueError(f"PDF not found: {pdf}")
        info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
        match = re.search(r"^Pages:\s+(\d+)$", info, re.M)
        if not match or int(match[1]) > 10:
            raise ValueError("Springer option A limit is 10 pages including references")
        result["pdf_pages"] = int(match[1])
    if placeholders:
        result["submission_status"] = "DRAFT: author funding and competing-interest declarations require confirmation"
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", type=Path)
    a = p.parse_args()
    try:
        import json
        print(json.dumps(check(pdf=a.pdf), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL paper source: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
