"""Check publication metrics, source disclosures, and build provenance."""
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import test_fpga_metrics
import manuscript_check
from fpga_metrics import collect, freeze


class PublicationTests(unittest.TestCase):
    def setUp(self):
        test_fpga_metrics.MetricsTests.setUp(self)
        self.metrics = collect(self.build, self.root)
        self.snapshot = self.root / "selected.json"
        freeze(self.metrics, self.snapshot)

    def test_submitted_paper_matches_selected_snapshot(self):
        selected = manuscript_check.load_metrics(manuscript_check.SNAPSHOT)
        self.assertEqual(manuscript_check.check_paper(selected), [])

    def test_stale_paper_metric_macro_is_rejected(self):
        source = manuscript_check.PAPER_SOURCE.read_text(encoding="utf-8")
        source = source.replace(
            r"\newcommand{\BaselineLE}{347}",
            r"\newcommand{\BaselineLE}{348}",
            1,
        )
        changed = self.root / "stale-main.tex"
        changed.write_text(source, encoding="utf-8")
        selected = manuscript_check.load_metrics(manuscript_check.SNAPSHOT)
        with patch.object(manuscript_check, "PAPER_SOURCE", changed):
            failures = manuscript_check.check_paper(selected)
        self.assertTrue(any("metric macro differs" in item for item in failures))

    def test_stale_abstract_metric_is_rejected(self):
        source = manuscript_check.PAPER_SOURCE.read_text(encoding="utf-8")
        source = source.replace(
            r"and \SecureFmax{}~MHz",
            r"and \BaselineFmax{}~MHz",
            1,
        )
        changed = self.root / "stale-abstract.tex"
        changed.write_text(source, encoding="utf-8")
        selected = manuscript_check.load_metrics(manuscript_check.SNAPSHOT)
        with patch.object(manuscript_check, "PAPER_SOURCE", changed):
            failures = manuscript_check.check_paper(selected)
        self.assertTrue(any("abstract differs" in item for item in failures))

    def test_changed_tracked_source_is_rejected_offline(self):
        selected = manuscript_check.load_metrics(self.snapshot, self.root)
        (self.root / "source.sv").write_text("changed RTL\n")
        with self.assertRaisesRegex(ValueError, "source changed"):
            manuscript_check.load_metrics(self.snapshot, self.root)
        self.assertIsNotNone(selected)

    def test_changed_live_artifact_and_incomplete_pair_are_rejected(self):
        with patch.object(manuscript_check, "collect", side_effect=lambda root: collect(root, self.root)):
            self.assertTrue(manuscript_check.check_builds(self.metrics, self.build))
            (self.path / "test.sof").write_text("different bitstream\n")
            with self.assertRaisesRegex(ValueError, "artifact hash"):
                manuscript_check.check_builds(self.metrics, self.build)
        empty = self.root / "absent"
        self.assertFalse(manuscript_check.check_builds(self.metrics, empty))
        (empty / "secure").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            manuscript_check.check_builds(self.metrics, empty)

    def test_snapshot_delta_and_timing_tampering_is_rejected(self):
        original = json.loads(self.snapshot.read_text())
        changed = json.loads(json.dumps(original))
        changed["results"]["comparison"]["logic_elements_delta"] += 1
        self.snapshot.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "deltas"):
            manuscript_check.load_metrics(self.snapshot, self.root)
        original["results"]["designs"]["secure"]["slack_ns_min"]["hold"] = -0.1
        self.snapshot.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, "timing slack"):
            manuscript_check.load_metrics(self.snapshot, self.root)

    def test_snapshot_refuses_overwrite_and_live_pair_changes(self):
        with self.assertRaises(FileExistsError):
            freeze(self.metrics, self.snapshot)
        changed = dict(self.metrics, comparison={})
        with patch.object(manuscript_check, "collect", return_value=changed):
            with self.assertRaisesRegex(ValueError, "differ from publication"):
                manuscript_check.check_builds(self.metrics, self.build)


if __name__ == "__main__":
    unittest.main()
