"""Software-only campaign/power/export checks, not physical board evidence."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_manifest import digest
from live_timing import frame_metrics
from long_campaign import command
from power_analysis import acceptance, parse_report
from power_simulate import (MAX_SEGMENT_MS, harness, simulation_do, tcl,
                            trim_vcd_window, validate_window, workload)
from publish_experiment import check_export, export


def report_text(confidence="High", comb=99, bad_pin=None):
    ports = ["MAX10_CLK1_50", "KEY0_N", "UART_RX", "UART_TX"] + [f"LEDR[{i}]" for i in range(10)]
    pin_rows = "\n".join(
        f"; {name} ; {'Input Pin' if name in ('MAX10_CLK1_50', 'KEY0_N', 'UART_RX') else 'Output Pin'} ; "
        f"0.0 ; {'Vectorless estimation' if name == bad_pin else 'Simulation (f1)'} ; "
        f"0.5 ; {'Vectorless estimation' if name == bad_pin else 'Simulation (f1)'} ;"
        for name in ports)
    return f'''; Device ; 10M50DAF484C7G ;
; Power Models ; Final ;
; Total Thermal Power Dissipation ; 0.130 W ;
; Core Dynamic Thermal Power Dissipation ; 15.0 mW ;
; Core Static Thermal Power Dissipation ; 90.0 mW ;
; I/O Thermal Power Dissipation ; 25.0 mW ;
; Power Estimation Confidence ; {confidence} ;
; -- Number of signals with Toggle Rate from Simulation ; 100 (99.0%) ; 8 (100.0%) ; 90 (99.0%) ; 10 ({comb}%) ;
; -- Simulation time nodes in unknown state ; 0.0% ; ; ; ;
; Automatically Compute Junction Temperature ; Off ; On ;
; Specified Junction Temperature ; 25 ; 25 ;
; Device Power Characteristics ; TYPICAL ; TYPICAL ;
; Signal Activities ;
{pin_rows}
'''


class ExtendedCampaignTests(unittest.TestCase):
    def test_measured_resolution_percentiles_and_span(self):
        data = {"sample_rate_hz": 200000, "baud": 9600,
                "reference_frame_start_samples": [100, 400, 700],
                "cipher_frame_start_samples": [310, 612, 914]}
        m = frame_metrics(data, 3)
        self.assertEqual(m["sample_period_us"], 5)
        self.assertAlmostEqual(m["delay_p50_us"], 1060)
        self.assertAlmostEqual(m["delay_p95_us"], 1070)
        self.assertAlmostEqual(m["reference_span_seconds"], .003 + 10/9600)
        for update in ({"sample_rate_hz": float("nan")},
                       {"cipher_frame_start_samples": [99, 400, 700]},
                       {"reference_frame_start_samples": [1, 1, 2]}):
            with self.assertRaises(ValueError):
                frame_metrics(dict(data, **update), 3)

    def test_power_gates_reject_low_and_defaults(self):
        parsed = parse_report(report_text())
        self.assertEqual(parsed["total_mw"], 130)
        self.assertEqual(parsed["pin_activity"]["UART_RX"]["toggle_source"], "Simulation (f1)")
        evidence = {k: True for k in ("byte_exact", "clock_io_mapping_verified", "steady_state",
            "postfit_functional_simulation", "same_workload_verified")}
        evidence.update(doubling_dynamic_change_percent=1.2, artifacts_sha256={"test": "hash"})
        self.assertEqual(acceptance(parsed, evidence), [])
        self.assertIn("used I/O pin lacks simulation activity: UART_TX",
                      acceptance(parse_report(report_text(bad_pin="UART_TX")), evidence))
        self.assertTrue(acceptance(parse_report(report_text("Low", .6)), evidence))
        self.assertTrue(acceptance(parsed, {}))
        evidence["doubling_dynamic_change_percent"] = float("nan")
        self.assertTrue(acceptance(parsed, evidence))

    def test_missing_power_rows_and_units_rejected(self):
        for text in ("", report_text().replace("0.130 W", "130 watts"),
                     report_text().replace("99.0%", "unavailable")):
            with self.assertRaises(ValueError):
                parse_report(text)

    def test_chunked_digest_preserves_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "large.bin"
            content = b"abc" * 800000
            p.write_bytes(content)
            self.assertEqual(digest(p), hashlib.sha256(content).hexdigest())

    def test_safe_command_and_tcl_paths(self):
        self.assertIn("'p;a b.sof'", command("quartus_pgm", "-o", "p;a b.sof"))
        self.assertEqual(tcl("space path"), "{space path}")
        with self.assertRaises(ValueError):
            tcl("} malicious {")
        self.assertIn("POSTFIT_FUNCTIONAL_PASS", harness("test_top", 0, 5000000))
        self.assertNotIn("[-1", harness("test_top", 0, 5000000))
        commands = simulation_do(Path("trace.vcd"), 100, 1000)
        self.assertEqual(commands.count("vcd file "), 1)
        self.assertIn("vcd add -r -nocell /tb/dut/implementation/*", commands)
        self.assertLess(commands.index("vcd flush"), commands.index("vcd off"))
        self.assertLess(commands.index("vcd off"), commands.index("run -all"))
        self.assertIn("run -all", commands)
        self.assertNotIn("closed.vcd", commands)
        self.assertNotIn("exec {", commands)
        validate_window(.002, MAX_SEGMENT_MS)
        for duration, segment_ms in ((.003, MAX_SEGMENT_MS), (.001, 3), (float("nan"), 1)):
            with self.assertRaises(ValueError):
                validate_window(duration, segment_ms)

    def test_vcd_window_crop_removes_post_window_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            vcd = Path(tmp) / "activity.vcd"
            vcd.write_text("$enddefinitions $end\n#0\n0!\n#1000\n1!\n#2000\n$dumpoff\nx!\n$end\n")
            self.assertEqual(trim_vcd_window(vcd, 1), 1000)
            result = vcd.read_text()
            self.assertIn("#1000", result)
            self.assertNotIn("#2000", result)
            self.assertNotIn("dumpoff", result)

    def test_public_export_requires_explicit_authority(self):
        with self.assertRaisesRegex(ValueError, "permission"):
            export(Path("absent"), Path("absent"), Path("absent"), Path("absent"))

    def test_published_pilot_reproduces(self):
        result = check_export(ROOT / "reference/experiments/p18-live-gps-1024")
        self.assertEqual(result, {"status": "PASS", "bytes": 1024, "nmea_sentences": 24})

    def test_failed_capture_not_power_workload(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "reference.bin").write_bytes(b"bad")
            (p / "comparison.json").write_text(json.dumps({"status": "FAIL"}))
            (p / "acquisition.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "approved"):
                workload(p, "live", 5, 1)

    def test_live_power_stimulus_waits_for_uart_idle_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            reference = p / "reference.bin"
            reference.write_bytes(b"AB")
            acquisition = {"sample_rate_hz": 200000,
                           "reference_frame_start_samples": [0, 4000],
                           "artifacts_sha256": {"reference.bin": digest(reference)}}
            acquisition_path = p / "acquisition.json"
            acquisition_path.write_text(json.dumps(acquisition))
            (p / "comparison.json").write_text(json.dumps({
                "status": "PASS",
                "acquisition_sha256": digest(acquisition_path)}))

            payload, edges, begin_ns, _ = workload(p, "live", 0, .002)

            self.assertEqual(payload[0], ord("A"))
            self.assertEqual(edges[0], begin_ns)
            self.assertGreaterEqual(begin_ns, round(3 * 1e9 / 9600))


if __name__ == "__main__":
    unittest.main()
