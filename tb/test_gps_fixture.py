"""Contract tests for the public GPS/NMEA replay; no board is required."""
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from gps_fixture import DEFAULT_FIXTURE, load_replay, metadata


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


if __name__ == "__main__":
    unittest.main()
