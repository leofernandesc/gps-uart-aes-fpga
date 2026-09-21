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
from gps_fixture import DEFAULT_FIXTURE, capture_metadata, load_replay, metadata, parse_payload, parse_window


class GPSReplayTests(unittest.TestCase):
    @staticmethod
    def sentence(body):
        checksum = 0
        for byte in body:
            checksum ^= byte
        return b"$" + body + f"*{checksum:02X}\r\n".encode()

    def test_identifier_printable_ascii_and_checksum_syntax(self):
        for payload in (b"$*00\r\n", self.sentence(b"GPTXT,\x00"), self.sentence(b"G,123"),
                        b"$GPTXT,*+1\r\n", b"$GPTXT,* 1\r\n"):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    parse_payload(payload)
        self.assertEqual(len(parse_payload(self.sentence(b"PUBX,00,1"))), 1)

    def test_length_includes_crlf_and_extended_profile_is_explicit(self):
        exact = self.sentence(b"GPTXT," + b"A" * 70)
        self.assertEqual(len(exact), 82)
        self.assertEqual(len(parse_payload(exact)), 1)
        longer = self.sentence(b"GPTXT," + b"A" * 72)
        with self.assertRaisesRegex(ValueError, "including CRLF"):
            parse_payload(longer)
        self.assertEqual(len(parse_payload(longer, max_sentence_bytes=128)), 1)

    def test_window_reports_offsets_without_modifying_raw_data(self):
        replay = load_replay()
        window = replay[7:-11]
        parsed, start, end = parse_window(window)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(start, window.find(b"\r\n") + 2)
        self.assertEqual(end, window.rfind(b"\r\n") + 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.bin"
            path.write_bytes(window)
            result = capture_metadata(path, allow_partial_edges=True)
            self.assertEqual(path.read_bytes(), window)
            self.assertEqual(result["bytes"], len(window))
            self.assertEqual(result["boundary_fragments"], {"prefix_bytes": start, "suffix_bytes": len(window) - end})

    def test_window_rejects_corrupt_interior_and_no_complete_sentence(self):
        with self.assertRaisesRegex(ValueError, "no complete"):
            parse_window(b"$GPRMC,fragment")
        valid = self.sentence(b"GPTXT,valid")
        corrupt = self.sentence(b"GPTXT,invalid").replace(b"invalid", b"Invalid")
        with self.assertRaisesRegex(ValueError, "checksum"):
            parse_window(b"fragment\r\n" + valid + corrupt + b"$GPRMC,tail")

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
