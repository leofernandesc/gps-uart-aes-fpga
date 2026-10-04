"""Supplemental STA must fail closed without touching published builds."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from timing_review import (RX_CHAIN, RESET_CHAIN, identified_qsf,
                           metastability_results, pulse_results, run)


def chain(source, identification="Automatic", rate="6.25", length=2):
    head = f"{RX_CHAIN}|rx_meta" if source == "UART_RX" else f"{RESET_CHAIN}|release_pipe[0]"
    fields = {"Source Node": source, "Synchronization Node": head,
              "Number of Synchronization Registers in Chain": length,
              "Method of Synchronizer Identification": identification,
              "Available Settling Time (ns)": "31.00",
              "Data Toggle Rate Used in MTBF Calculation (millions of transitions / sec)": rate,
              "Worst-Case MTBF (years)": "Not Calculated",
              "Typical MTBF (years)": "Not Calculated",
              "Included in Design MTBF": "No"}
    return "\n".join(f"; {name} ; {value} ;" for name, value in fields.items())


class TimingReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        self.pulses = "\n".join(f"REVIEW corner={c} check=min_pulse_width slack_ns=9.250" for c in (1, 2, 3))
        self.pulses += "\nPASS: 3 supplemental timing corners audited\n"
        (self.path / "review.log").write_text(self.pulses)
        self.write_chains()

    def write_chains(self, identified=False):
        text = "Number of Synchronizer Chains Found: 2\n"
        method = "User Specified" if identified else "Automatic"
        for index, source in enumerate(("UART_RX", "KEY0_N"), 1):
            rate = "0.0096" if identified and source == "UART_RX" else "6.25"
            text += f"\nSynchronizer Chain #{index}: Worst-Case MTBF is Not Calculated\n"
            text += chain(source, method, rate) + "\n"
        for c in (1, 2, 3):
            (self.path / f"metastability_corner{c}.rpt").write_text(text)

    def test_three_positive_pulse_corners(self):
        self.assertEqual(pulse_results(self.path)["slack_ns_by_corner"], [9.25] * 3)

    def test_missing_duplicate_negative_nonfinite_and_error_pulses(self):
        first = self.pulses.splitlines()[0]
        for bad in (self.pulses.replace(first, ""), first + "\n" + self.pulses,
                    self.pulses.replace("9.250", "-0.1", 1),
                    self.pulses.replace("9.250", "nan", 1),
                    self.pulses.replace("9.250", "1e999", 1),
                    self.pulses.replace("PASS:", "FAIL:"), self.pulses + "Error (1): failure\n"):
            with self.subTest(bad=bad[:80]):
                (self.path / "review.log").write_text(bad)
                with self.assertRaises(ValueError):
                    pulse_results(self.path)

    def test_auto_chain_report_does_not_claim_mtbf(self):
        report = metastability_results(self.path)
        self.assertEqual(len(report), 3)
        self.assertEqual(report[0]["chains"][0]["worst_mtbf_years"], "Not Calculated")
        with self.assertRaisesRegex(ValueError, "not recognized"):
            metastability_results(self.path, identified=True)

    def test_explicit_identification_and_toggle_assumptions(self):
        self.write_chains(identified=True)
        results = metastability_results(self.path, identified=True)
        self.assertEqual(results[0]["chains"][1]["toggle_millions_per_second"], 0.0096)
        report = self.path / "metastability_corner2.rpt"
        report.write_text(report.read_text().replace("0.0096", "6.25"))
        with self.assertRaisesRegex(ValueError, "toggle assumption"):
            metastability_results(self.path, identified=True)

    def test_missing_wrong_head_stage_count_and_source_rejected(self):
        report = self.path / "metastability_corner1.rpt"
        original = report.read_text()
        for bad in (original.replace("Found: 2", "Found: 1"),
                    original.replace("|rx_meta", "|bad"),
                    original.replace("in Chain ; 2", "in Chain ; 1"),
                    original.replace("UART_RX", "OTHER_RX")):
            with self.subTest(bad=bad[:80]):
                report.write_text(bad)
                with self.assertRaises(ValueError):
                    metastability_results(self.path)

    def test_profile_paths_and_assignments_are_isolated(self):
        source = self.path / "original.qsf"
        rtl = self.path / "source with spaces.sv"
        rtl.write_text("module test; endmodule\n")
        text = 'set_global_assignment -name SYSTEMVERILOG_FILE "source with spaces.sv"\n'
        text += 'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY old-build\n'
        source.write_text(text)
        output = self.path / "new-fit"
        output.mkdir()
        generated = identified_qsf(source, output, "baseline").read_text()
        self.assertEqual(source.read_text(), text)
        self.assertIn(str(rtl.resolve()), generated)
        self.assertNotIn("old-build", generated)
        self.assertEqual(generated.count("-name SYNCHRONIZER_IDENTIFICATION"), 4)
        self.assertIn(f'-to "{RX_CHAIN}|rx_meta"', generated)
        self.assertNotIn("-to {", generated)
        self.assertIn("SYNCHRONIZER_TOGGLE_RATE 9600", generated)
        self.assertIn("SYNCHRONIZER_TOGGLE_RATE 6250000", generated)

    def test_success_exit_does_not_hide_ignored_assignments(self):
        def critical_warning(command, cwd, stdout, stderr):
            stdout.write('Critical Warning (136021): Ignored assignment SYNCHRONIZER_TOGGLE_RATE\n')
            return subprocess.CompletedProcess(command, 0)
        with patch("timing_review.subprocess.run", side_effect=critical_warning):
            with self.assertRaisesRegex(ValueError, "critical warning"):
                run(["quartus_sh"], self.path, self.path / "compile.log")


if __name__ == "__main__":
    unittest.main()
