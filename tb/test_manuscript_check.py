"""Reject stale manuscript numbers and broken publication provenance."""
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import test_fpga_metrics
import manuscript_check
from fpga_metrics import collect, comparison_table, freeze


class PublicationTests(unittest.TestCase):
    def setUp(self):
        test_fpga_metrics.MetricsTests.setUp(self)
        self.metrics = collect(self.build, self.root)
        self.snapshot = self.root / "selected.json"
        freeze(self.metrics, self.snapshot)
        self.draft = self.root / "draft.md"

    def write_draft(self, label="English"):
        heading = "Abstract" if label == "English" else "Resumo"
        frequency = "80.00" if label == "English" else "80,00"
        self.draft.write_text(f"## {heading}\n400 elements, 200 registers, {frequency} MHz.\n"
                              "## Results\n" + comparison_table(self.metrics, label) + "\n")

    def test_selected_snapshot_and_bilingual_tables(self):
        selected = manuscript_check.load_metrics(self.snapshot, self.root)
        for label in ("English", "Portuguese"):
            self.write_draft(label)
            self.assertEqual(manuscript_check.check_draft(label, self.draft, (), selected), [])

    def test_stale_table_is_rejected_even_with_correct_numbers_elsewhere(self):
        self.write_draft()
        raw = self.draft.read_text().replace("| 400 | 400 |", "| 400 | 401 |", 1)
        self.draft.write_text(raw + "\nCorrect secure count: 400\n")
        self.assertTrue(manuscript_check.check_draft("English", self.draft, (), self.metrics))

    def test_stale_abstract_is_rejected_even_with_correct_table(self):
        self.write_draft()
        self.draft.write_text(self.draft.read_text().replace("80.00 MHz.", "79.00 MHz.", 1))
        failures = manuscript_check.check_draft("English", self.draft, (), self.metrics)
        self.assertTrue(any("abstract differs" in failure for failure in failures))

    def test_wrong_delta_and_duplicate_rows_are_rejected(self):
        self.write_draft()
        original = self.draft.read_text()
        self.draft.write_text(original.replace("+0.00%", "+1.00%", 1))
        self.assertTrue(manuscript_check.check_draft("English", self.draft, (), self.metrics))
        row = next(line for line in original.splitlines() if line.startswith("| Registers |"))
        self.draft.write_text(original + row + "\n")
        self.assertTrue(manuscript_check.check_draft("English", self.draft, (), self.metrics))

    def test_changed_tracked_source_is_rejected_offline(self):
        (self.root / "source.sv").write_text("changed RTL\n")
        with self.assertRaisesRegex(ValueError, "source changed"):
            manuscript_check.load_metrics(self.snapshot, self.root)

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
