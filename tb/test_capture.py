"""PC comparison and Linux pseudo-terminal checks; not USB/board validation."""
import importlib.util
import json
import os
from pathlib import Path
import pty
import subprocess
import sys
import tempfile
import termios
import threading
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("capture", SCRIPTS / "capture.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
from ctr_vectors import crypt


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.plain = bytes(range(256)) + b"\r\n\x00\xff"
        self.key, self.nonce = bytes(range(16)), bytes(range(12))
        self.context = {"mode": "aes-128-ctr", "bytes": len(self.plain), "key_hex": self.key.hex(),
                        "nonce_hex": self.nonce.hex(), "initial_counter": 255}
        self.cipher = crypt(self.key, self.nonce, 255, self.plain)

    def test_modes_and_binary_preservation(self):
        for payload, context in ((self.cipher, self.context), (self.plain, {"mode": "baseline", "bytes": len(self.plain)})):
            report, recovered = capture.compare(self.plain, payload, context)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(recovered, self.plain)

    def test_truncated_extra_and_corrupt(self):
        for payload, offset in ((self.cipher[:-1], len(self.plain) - 1), (self.cipher + b"x", len(self.plain)),
                                (self.cipher[:17] + bytes([self.cipher[17] ^ 1]) + self.cipher[18:], 17)):
            report, _ = capture.compare(self.plain, payload, self.context)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["first_divergence_offset"], offset)

    def test_bad_reference_and_explicit_invalidity(self):
        for reference, reasons in ((self.plain[:-1], []), (self.plain, ["reset"]), (self.plain, ["overflow", "framing"])):
            self.assertEqual(capture.compare(reference, self.cipher, self.context, reasons)[0]["status"], "FAIL")

    def test_context_validation(self):
        for patch in ({"initial_counter": 0xffffffff}, {"initial_counter": -1}, {"initial_counter": True},
                      {"bytes": 0}, {"bytes": True}, {"bytes": 17, "initial_counter": 0xffffffff},
                      {"key_hex": "00"}, {"nonce_hex": "xyz"}, {"mode": "ecb"}):
            with self.assertRaises(ValueError):
                capture.compare(self.plain, self.cipher, self.context | patch)

    def test_cli_exit_codes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="uart-compare-") as tmp:
            root = Path(tmp)
            (root / "input.bin").write_bytes(self.plain)
            (root / "output.bin").write_bytes(self.cipher)
            (root / "context.json").write_text(json.dumps(self.context))
            command = [sys.executable, str(SCRIPTS / "capture.py"), "compare", "--reference", str(root / "input.bin"),
                       "--received", str(root / "output.bin"), "--context", str(root / "context.json"),
                       "--report", str(root / "report.json"), "--recovered", str(root / "recovered.bin")]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((root / "recovered.bin").read_bytes(), self.plain)
            self.assertEqual((root / "recovered.bin").stat().st_mode & 0o777, 0o600)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            command[-1] = str(root / "invalid.bin")
            command[-3] = str(root / "invalid.json")
            self.assertEqual(subprocess.run(command + ["--invalid", "framing"], capture_output=True).returncode, 1)


class SerialTests(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.port = os.ttyname(self.slave)
        self.tmp = tempfile.TemporaryDirectory(prefix="uart-record-")
        self.path = Path(self.tmp.name) / "serial.bin"

    def tearDown(self):
        os.close(self.master)
        os.close(self.slave)
        self.tmp.cleanup()

    def test_raw_capture_and_settings_restored(self):
        payload = bytes(range(256)) + b"\x11\x13\r\n\x00"
        previous = termios.tcgetattr(self.slave)
        ready = threading.Event()
        def send():
            if ready.wait(2):
                os.write(self.master, payload[:13])
                os.write(self.master, payload[13:])
        sender = threading.Thread(target=send)
        sender.start()
        try:
            result = capture.record_serial(self.port, self.path, len(payload), 2, ready.set)
        finally:
            sender.join(timeout=3)
        self.assertEqual(result["status"], "CAPTURED")
        self.assertEqual(self.path.read_bytes(), payload)
        self.assertEqual(termios.tcgetattr(self.slave), previous)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_timeout_preserves_partial(self):
        result = capture.record_serial(self.port, self.path, 4, 0.05, lambda: os.write(self.master, b"ab"))
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["error"], "timeout")
        self.assertEqual(self.path.read_bytes(), b"ab")

    def test_refuses_overwrite_and_restores_port(self):
        self.path.write_bytes(b"old capture")
        previous = termios.tcgetattr(self.slave)
        with self.assertRaises(FileExistsError):
            capture.record_serial(self.port, self.path, 4, 0.05)
        self.assertEqual(self.path.read_bytes(), b"old capture")
        self.assertEqual(termios.tcgetattr(self.slave), previous)


if __name__ == "__main__":
    unittest.main()
