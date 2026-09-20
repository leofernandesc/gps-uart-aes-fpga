"""Contract tests for the public GPS/NMEA replay; no board is required."""
import sys
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from gps_fixture import DEFAULT_FIXTURE, capture_metadata, load_replay, metadata, parse_payload


class GPSReplayTests(unittest.TestCase):
    def test_public_m8_nmea_replay_is_well_formed(self):
        result = metadata(DEFAULT_FIXTURE)
        payload = load_replay(DEFAULT_FIXTURE)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["sentences"], 5)
        self.assertEqual(result["bytes"], len(payload))
        self.assertEqual(payload.count(b"\r\n"), 5)
        self.assertNotIn(b"\n", payload.replace(b"\r\n", b""))
        self.assertTrue(payload.startswith(b"$GPRMC,"))
        self.assertTrue(payload.endswith(b"*50\r\n"))

    def test_raw_capture_parser_accepts_complete_replay(self):
        payload = load_replay(DEFAULT_FIXTURE)
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "gps.bin"
            capture.write_bytes(payload)
            parsed = parse_payload(payload)
            result = capture_metadata(capture)
        self.assertEqual(len(parsed), 5)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["bytes"], 309)
        self.assertEqual(result["sentence_types"], {"GPGGA": 1, "GPGSA": 1, "GPRMC": 1, "GPTXT": 1, "GPGSV": 1})

    def test_raw_capture_parser_rejects_corruption_and_incomplete_framing(self):
        payload = bytearray(load_replay(DEFAULT_FIXTURE))
        payload[1] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            parse_payload(bytes(payload))
        with self.assertRaisesRegex(ValueError, "complete CRLF"):
            parse_payload(load_replay(DEFAULT_FIXTURE)[:-1])
        with self.assertRaisesRegex(ValueError, "CRLF"):
            parse_payload(load_replay(DEFAULT_FIXTURE).replace(b"\r\n", b"\n"))

    def test_capture_cli_writes_private_report(self):
        payload = load_replay(DEFAULT_FIXTURE)
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "gps.bin"
            report = Path(directory) / "gps.json"
            capture.write_bytes(payload)
            command = [
                sys.executable,
                str(SCRIPTS / "gps_capture.py"),
                "--input",
                str(capture),
                "--report",
                str(report),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            result = json.loads(report.read_text(encoding="utf-8"))
            mode = stat.S_IMODE(os.stat(report).st_mode)
            repeated = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PASS GPS capture: 5 sentences, 309 bytes", completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(mode, 0o600)
        self.assertEqual(repeated.returncode, 1)
        self.assertIn("File exists", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
