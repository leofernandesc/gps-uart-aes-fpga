"""Fail-closed tests: invalid evidence must never become an article table."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from build_manifest import digest
from fpga_metrics import BUILD_PASS, _fit_metrics, _timing_metrics, collect


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "source.sv").write_text("module source; endmodule\n")
        self.build = self.root / "build"
        for design in ("baseline", "secure"):
            path = self.build / design
            path.mkdir(parents=True)
            (path / "build-status.txt").write_text(BUILD_PASS + "\n")
            (path / "test.fit.summary").write_text(
                "Fitter Status : Successful\nQuartus Prime Version : Test 1\n"
                "Device : 10M50DAF484C7G\nTotal logic elements : 400 / 49,760\n"
                "Total registers : 200\nTotal memory bits : 8,192\nTotal pins : 14\nTotal PLLs : 0\n")
            for corner in range(1, 4):
                (path / f"fmax_corner{corner}.rpt").write_text("; 80.00 MHz ; 80.00 MHz ; clock ;\n")
            (path / "timing-audit.log").write_text("\n".join(
                f"AUDIT corner={corner} check={check} slack_ns=+0.125"
                for corner in range(1, 4) for check in ("setup", "hold", "recovery", "removal")) + "\nPASS: 3 timing corners audited\n")
            for name in ("test.sof", "clocks.rpt", "check_timing.rpt", "unconstrained.rpt", "tool-version.txt", "compile.log"):
                (path / name).write_text("fixture\n")
            manifest = {"schema": 1, "status": "PASS", "board": "de10_lite", "design": design,
                        "device": "10M50DAF484C7G", "seed": 1, "clock_hz": 50_000_000,
                        "baud": 9600, "fifo_depth": 1024, "shared_rtl_sha256": "same",
                        "sources_sha256": {"source.sv": digest(self.root / "source.sv")},
                        "artifacts_sha256": {p.name: digest(p) for p in path.iterdir() if p.name != "build-status.txt"}}
            (path / "build-manifest.json").write_text(json.dumps(manifest))
        self.path = self.build / "secure"

    def test_complete_pair(self):
        result = collect(self.build, self.root)
        self.assertEqual(result["designs"]["secure"]["slack_ns_min"]["setup"], 0.125)

    def test_signed_negative_slack_is_rejected(self):
        audit = self.path / "timing-audit.log"
        audit.write_text(audit.read_text().replace("+0.125", "-0.125", 1))
        with self.assertRaisesRegex(ValueError, "negative slack"):
            _timing_metrics(self.path)

    def test_missing_duplicate_or_nonfinite_checks_are_rejected(self):
        audit = self.path / "timing-audit.log"
        original = audit.read_text()
        first = original.splitlines()[0]
        for changed in (original.replace(first + "\n", ""), first + "\n" + original,
                        original.replace("+0.125", "nan", 1), original.replace("+0.125", "1e999", 1),
                        original.replace("PASS:", "FAIL:")):
            with self.subTest(changed=changed[:100]):
                audit.write_text(changed)
                with self.assertRaises(ValueError):
                    _timing_metrics(self.path)

    def test_missing_fmax_corner_or_failed_fit_is_rejected(self):
        (self.path / "fmax_corner2.rpt").unlink()
        with self.assertRaisesRegex(ValueError, "corner mismatch"):
            _timing_metrics(self.path)
        report = self.path / "test.fit.summary"
        report.write_text(report.read_text().replace("Successful", "Failed"))
        with self.assertRaisesRegex(ValueError, "fitter"):
            _fit_metrics(self.path)

    def test_failed_build_is_rejected(self):
        (self.path / "build-status.txt").write_text("FAIL: stale SOF\n")
        with self.assertRaisesRegex(ValueError, "build did not pass"):
            collect(self.build, self.root)

    def test_modified_reports_and_stale_sources_are_rejected(self):
        report = self.path / "fmax_corner1.rpt"
        original = report.read_text()
        report.write_text(original.replace("80.00", "90.00"))
        with self.assertRaisesRegex(ValueError, "artifact hash"):
            collect(self.build, self.root)
        report.write_text(original)
        (self.root / "source.sv").write_text("changed RTL\n")
        with self.assertRaisesRegex(ValueError, "stale build"):
            collect(self.build, self.root)

    def test_incompatible_pair_is_rejected(self):
        manifest_path = self.path / "build-manifest.json"
        original = json.loads(manifest_path.read_text())
        for field in ("seed", "clock_hz", "fifo_depth", "shared_rtl_sha256", "device"):
            with self.subTest(field=field):
                changed = dict(original, **{field: "different"})
                manifest_path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    collect(self.build, self.root)


if __name__ == "__main__":
    unittest.main()
