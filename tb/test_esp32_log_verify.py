"""Tests for fail-closed verification of ESP32 physical-bench logs."""

import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "esp32_log_verify.py"
spec = importlib.util.spec_from_file_location("esp32_log_verify", SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def result_line(sequence, mode, received, **changes):
    values = {
        "seq": sequence,
        "mode": mode,
        "tx": "55A500FF3C",
        "rx": received.hex().upper(),
        "rx_len": len(received),
        "same": int(received == verifier.DEFAULT_VECTOR),
        "timeout": 0,
        "extra": 0,
        "frame_err": 0,
        "parity_err": 0,
        "fifo_ovf": 0,
        "buffer_full": 0,
        "break": 0,
        "write_err": 0,
        "tx_timeout": 0,
        "host_window_us": 16000,
    }
    values.update(changes)
    fields = " ".join(f"{name}={value}" for name, value in values.items())
    return f"I (1234) esp32_uart_host: RESULT {fields}"


class ESP32LogVerifierTests(unittest.TestCase):
    def test_baseline_four_trials_pass_with_monitor_prefix(self):
        old_session = result_line(87, "baseline", verifier.DEFAULT_VECTOR)
        current_session = "\n".join(
            result_line(index, "baseline", verifier.DEFAULT_VECTOR)
            for index in range(1, 5))
        text = (old_session + "\nI (20) esp32_uart_host: " +
                verifier.SESSION_MARKER + "\n" + current_session)
        records = verifier.parse_results(text)
        report = verifier.verify(records, "baseline")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["bytes"], 20)

    def test_secure_four_trials_cross_mask_boundary(self):
        plain = verifier.DEFAULT_VECTOR * 4
        cipher = verifier.crypt(
            verifier.PUBLIC_KEY, verifier.PUBLIC_NONCE,
            verifier.PUBLIC_COUNTER, plain)
        text = "\n".join(
            result_line(index + 1, "secure", cipher[index * 5:(index + 1) * 5])
            for index in range(4))
        report = verifier.verify(verifier.parse_results(text), "secure")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["received_hex"],
                         "5B722565E145B4E1A6EC5BC4B16D6845612EFC93")

    def test_transport_error_and_nonconsecutive_sequence_fail(self):
        text = "\n".join((
            result_line(1, "baseline", verifier.DEFAULT_VECTOR),
            result_line(3, "baseline", verifier.DEFAULT_VECTOR, frame_err=1),
            result_line(4, "baseline", verifier.DEFAULT_VECTOR),
            result_line(5, "baseline", verifier.DEFAULT_VECTOR),
        ))
        report = verifier.verify(verifier.parse_results(text), "baseline")
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("expected 2" in item for item in report["failures"]))
        self.assertTrue(any("frame_err=1" in item for item in report["failures"]))

    def test_ciphertext_corruption_fails_recovery(self):
        cipher = bytearray(verifier.crypt(
            verifier.PUBLIC_KEY, verifier.PUBLIC_NONCE,
            verifier.PUBLIC_COUNTER, verifier.DEFAULT_VECTOR * 4))
        cipher[7] ^= 1
        text = "\n".join(
            result_line(index + 1, "secure", cipher[index * 5:(index + 1) * 5])
            for index in range(4))
        report = verifier.verify(verifier.parse_results(text), "secure")
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("byte offset 7" in item for item in report["failures"]))

    def test_cli_private_report_and_no_overwrite(self):
        text = "\n".join(
            result_line(index, "baseline", verifier.DEFAULT_VECTOR)
            for index in range(1, 5)) + "\n"
        with tempfile.TemporaryDirectory(prefix="esp32-log-") as temporary:
            root = Path(temporary)
            log = root / "monitor.log"
            report = root / "report.json"
            log.write_text(text, encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "--input", str(log),
                       "--mode", "baseline", "--report", str(report)]
            first = subprocess.run(command, capture_output=True, text=True,
                                   check=False)
            saved = json.loads(report.read_text(encoding="utf-8"))
            mode = stat.S_IMODE(report.stat().st_mode)
            repeated = subprocess.run(command, capture_output=True, text=True,
                                      check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(saved["status"], "PASS")
        self.assertEqual(mode, 0o600)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("File exists", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
