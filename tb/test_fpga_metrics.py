"""Negative and completeness tests for Quartus post-fit metric extraction."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fpga_metrics import collect


def write_build(root: Path, design: str, slack: str = "1.000") -> None:
    path = root / design
    path.mkdir(parents=True)
    (path / f"{design}.fit.summary").write_text(
        "Total logic elements : 10\nTotal registers : 4\n"
        "Total memory bits : 8192\nTotal pins : 14\nTotal PLLs : 1\n"
        "Device : 10M50DAF484C7G\nQuartus Prime Version : test\n",
        encoding="utf-8",
    )
    (path / "fmax_corner1.rpt").write_text("; 100.00 MHz ; 100.00 MHz ;\n", encoding="utf-8")
    (path / "timing-audit.log").write_text(
        "\n".join(
            [
                *(f"AUDIT corner=1 check={check} slack_ns={slack}" for check in ("setup", "hold", "recovery", "removal")),
                "PASS: 1 timing corners audited",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    (path / "build-status.txt").write_text("PASS: Quartus compilation\n", encoding="utf-8")


class FPGAMetricsTests(unittest.TestCase):
    def test_accepts_complete_positive_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_build(root, "baseline")
            write_build(root, "secure")
            result = collect(root)
        self.assertEqual(result["designs"]["secure"]["slack_ns_min"]["setup"], 1.0)

    def test_rejects_negative_slack_even_if_text_has_a_pass_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_build(root, "baseline", "-0.125")
            write_build(root, "secure")
            with self.assertRaisesRegex(ValueError, "negative timing slack"):
                collect(root)

    def test_rejects_missing_corner_or_build_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_build(root, "baseline")
            write_build(root, "secure")
            (root / "secure" / "build-status.txt").unlink()
            with self.assertRaisesRegex(ValueError, "build-status"):
                collect(root)


if __name__ == "__main__":
    unittest.main()
