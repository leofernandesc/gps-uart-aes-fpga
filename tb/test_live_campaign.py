"""Software tests only; do not count these as AD2/FPGA physical results."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from ad2_live_capture import UARTDecoder, assess
from bench_build import project_text
from capture import private_file
from context import create_context, claim_capture
from ctr_vectors import crypt
from gps_fixture import load_replay, parse_window
from stress_fixture import make_payload


def waveform(payload, bit=0, rate=1000000, baud=9600, bad_stop=False):
    bits = [1] * 4
    for index, value in enumerate(payload):
        bits += [0] + [(value >> n) & 1 for n in range(8)] + [0 if bad_stop and index == 0 else 1]
    bits += [1] * 4
    # Edge-rounded sampling models fractional samples/bit.
    samples = bytearray()
    for i, level in enumerate(bits):
        count = round((i + 1) * rate / baud) - round(i * rate / baud)
        samples.extend(bytes([level << bit]) * count)
    return bytes(samples)


class LiveCampaignTests(unittest.TestCase):
    def test_decoder_binary_boundaries_and_chunk_splits(self):
        for count in (1, 5, 15, 16, 17, 64):
            payload = bytes((index * 71) & 255 for index in range(count))
            for bit in (0, 1):
                with self.subTest(count=count, bit=bit):
                    samples = waveform(payload, bit)
                    d = UARTDecoder(1000000, bit=bit)
                    for index in range(0, len(samples), 31):
                        d.feed(samples[index:index + 31])
                    self.assertEqual(bytes(d.data), payload)
                    self.assertEqual(d.framing_errors, 0)
                    self.assertEqual(len(d.starts), count)
                    self.assertTrue(all(a < b for a, b in zip(d.starts, d.starts[1:])))

    def test_stop_error_and_initial_partial_frame(self):
        d = UARTDecoder(1000000)
        d.feed(waveform(b"\x00", bad_stop=True))
        self.assertEqual(d.framing_errors, 1)
        self.assertEqual(d.data, b"")
        d = UARTDecoder(1000000)
        d.feed(b"\x00" * 250 + waveform(b"\x55"))
        self.assertEqual(d.data, b"\x55")

    def test_rate_validation_and_limit(self):
        with self.assertRaises(ValueError):
            UARTDecoder(10000)
        d = UARTDecoder(1000000, limit=1)
        d.feed(waveform(b"\x55\xa5"))
        self.assertEqual(d.data, b"\x55")

    def test_lower_rates_and_dio2_across_all_byte_values(self):
        payload = bytes(range(256))
        for rate in (100000000 / 156, 100000000 / 143):
            for bit in (0, 2):
                with self.subTest(rate=rate, bit=bit):
                    d = UARTDecoder(rate, bit=bit)
                    samples = waveform(payload, bit=bit, rate=rate)
                    for index in range(0, len(samples), 31):
                        d.feed(samples[index:index + 31])
                    self.assertEqual(bytes(d.data), payload)
                    self.assertEqual(d.framing_errors, 0)
                    self.assertEqual(d.false_starts, 0)

    def test_common_window_secure_and_corruption(self):
        reference = load_replay()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            create_context("aes-128-ctr", len(reference), p / "context.json", p / "registry.json",
                           key_hex="000102030405060708090a0b0c0d0e0f")
            context = json.loads((p / "context.json").read_text())
            cipher = crypt(bytes.fromhex(context["key_hex"]), bytes.fromhex(context["nonce_hex"]), 0, reference)
            acquisition = {"ready_idle_verified": True, "invalid_reasons": [], **dict.fromkeys(
                ("lost_samples", "corrupt_samples", "reference_framing_errors", "cipher_framing_errors",
                 "reference_false_starts", "cipher_false_starts"), 0)}
            result, recovered = assess(reference, cipher, cipher, context, acquisition)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(recovered, reference)
            for field in ("lost_samples", "corrupt_samples", "reference_framing_errors", "cipher_framing_errors"):
                with self.subTest(field=field):
                    result, _ = assess(reference, cipher, cipher, context, {**acquisition, field: 1})
                    self.assertEqual(result["status"], "FAIL")
            for rx, cp in ((cipher[1:], cipher), (b"\0" + cipher, cipher), (cipher, cipher[:-1])):
                result, _ = assess(reference, rx, cp, context, acquisition)
                self.assertEqual(result["status"], "FAIL")
            claim_capture(context, p / "registry.json")
            with self.assertRaises(ValueError):
                claim_capture(context, p / "registry.json")

    def test_stress_repetition_does_not_repeat_trailing_fragment(self):
        reference = b"partial\r\n" + load_replay() + b"$GNRMC,partial"
        payload, report = make_payload(reference, 1048576)
        self.assertEqual(len(payload), 1048576)
        self.assertEqual(report["source_suffix_excluded"], 14)
        sentences, _, _ = parse_window(payload)
        self.assertGreater(len(sentences), 1000)
        self.assertNotIn(b"partial", payload)

    def test_qsf_changes_only_paths_not_architecture_or_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "context_params.sv").write_text("test")
            source = ROOT / "fpga/de10_lite/secure/uart_secure.qsf"
            result = project_text(source, p)
            self.assertIn(str(p / "context_params.sv"), result)
            old = [line for line in source.read_text().splitlines() if "_FILE " not in line and "PROJECT_OUTPUT_DIRECTORY" not in line]
            new = [line for line in result.splitlines() if "_FILE " not in line and "PROJECT_OUTPUT_DIRECTORY" not in line]
            self.assertEqual(old, new)
            self.assertNotIn("FORCED IF ASYNCHRONOUS", result)

    def test_private_file_collision_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.bin"
            with private_file(p, True) as stream:
                stream.write(b"evidence")
            with self.assertRaises(FileExistsError):
                private_file(p, True)
            self.assertEqual(p.read_bytes(), b"evidence")
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
