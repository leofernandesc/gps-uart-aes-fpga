"""Tests for private experiment-context and nonce-registry handling."""
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parent.parent / "scripts/context.py"
spec = importlib.util.spec_from_file_location("context_tool", SCRIPT)
context_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_tool)


class ContextTests(unittest.TestCase):
    def test_cli_random_key_stays_private_and_only_fingerprint_is_registered(self):
        with tempfile.TemporaryDirectory(prefix="uart-random-context-") as tmp:
            root = Path(tmp)
            output = root / "context.json"
            registry = root / "nonce-registry.json"
            stdout = io.StringIO()
            with patch.object(sys, "argv", [str(SCRIPT), "new", "--mode", "aes-128-ctr",
                                             "--bytes", "1024", "--registry", str(registry),
                                             "--output", str(output), "--random-key"]), \
                    redirect_stdout(stdout):
                self.assertEqual(context_tool.main(), 0)
            context = json.loads(output.read_text())
            entry = json.loads(registry.read_text())["contexts"][0]
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertEqual(len(bytes.fromhex(context["key_hex"])), 16)
            self.assertNotEqual(context["key_hex"], "000102030405060708090a0b0c0d0e0f")
            self.assertNotIn("key_hex", entry)
            self.assertNotIn(context["key_hex"], stdout.getvalue())

    def test_secure_context_requires_explicit_key_generation_or_value(self):
        with tempfile.TemporaryDirectory(prefix="uart-key-choice-") as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                context_tool.create_context("aes-128-ctr", 1, root / "missing.json",
                                            root / "registry.json")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                context_tool.create_context("aes-128-ctr", 1, root / "both.json",
                                            root / "registry.json",
                                            "00112233445566778899aabbccddeeff",
                                            random_key=True)

    def test_secure_context_is_private_and_registered(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            output = root / "context.json"
            registry = root / "nonce-registry.json"
            context = context_tool.create_context(
                "aes-128-ctr", 1024, output, registry,
                key_hex="00112233445566778899aabbccddeeff")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(registry.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(context["nonce_hex"]), 24)
            saved = json.loads(output.read_text())
            entries = json.loads(registry.read_text())["contexts"]
            self.assertEqual(saved["context_id"], context["context_id"])
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["nonce_hex"], context["nonce_hex"])
            self.assertNotIn("key_hex", entries[0])

    def test_same_key_nonce_cannot_be_reused(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            registry = root / "nonce-registry.json"
            key = "00112233445566778899aabbccddeeff"
            nonce = "101112131415161718191a1b"
            context_tool.create_context("aes-128-ctr", 1, root / "one.json", registry,
                                        key, nonce)
            with self.assertRaises(ValueError):
                context_tool.create_context("aes-128-ctr", 1, root / "two.json", registry,
                                            key, nonce)
            self.assertFalse((root / "two.json").exists())

    def test_same_nonce_with_different_key_is_allowed(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            registry = root / "nonce-registry.json"
            nonce = "101112131415161718191a1b"
            context_tool.create_context("aes-128-ctr", 1, root / "one.json", registry,
                                        "00112233445566778899aabbccddeeff", nonce)
            context_tool.create_context("aes-128-ctr", 1, root / "two.json", registry,
                                        "ffeeddccbbaa99887766554433221100", nonce)
            self.assertEqual(len(json.loads(registry.read_text())["contexts"]), 2)

    def test_baseline_has_no_crypto_context(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            context = context_tool.create_context("baseline", 70, root / "baseline.json")
            self.assertEqual(context["mode"], "baseline")
            self.assertNotIn("key_hex", json.loads((root / "baseline.json").read_text()))

    def test_counter_boundaries_and_existing_output(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            registry = root / "nonce-registry.json"
            key = "00112233445566778899aabbccddeeff"
            with self.assertRaises(ValueError):
                context_tool.create_context("aes-128-ctr", 17, root / "bad.json", registry,
                                            key, None, 0xffffffff)
            context_tool.create_context("baseline", 1, root / "same.json")
            with self.assertRaises(FileExistsError):
                context_tool.create_context("baseline", 1, root / "same.json")

    def test_render_secure_context_as_private_systemverilog_package(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            context_path = root / "secure.json"
            package_path = root / "context_params.sv"
            context_tool.create_context(
                "aes-128-ctr", 32, context_path, root / "registry.json",
                key_hex="00112233445566778899aabbccddeeff",
                nonce_hex="101112131415161718191a1b",
                initial_counter=0x12345678,
            )
            rendered = context_tool.render_context_sv(
                context_path, package_path, expected_mode="aes-128-ctr")
            self.assertEqual(rendered["mode"], "aes-128-ctr")
            self.assertEqual(stat.S_IMODE(package_path.stat().st_mode), 0o600)
            package = package_path.read_text()
            self.assertIn("128'h00112233445566778899aabbccddeeff", package)
            self.assertIn("96'h101112131415161718191a1b", package)
            self.assertIn("32'h12345678", package)

    def test_render_rejects_wrong_build_mode(self):
        with tempfile.TemporaryDirectory(prefix="uart-context-") as tmp:
            root = Path(tmp)
            context_path = root / "baseline.json"
            context_tool.create_context("baseline", 1, context_path)
            with self.assertRaises(ValueError):
                context_tool.render_context_sv(
                    context_path, root / "context_params.sv",
                    expected_mode="aes-128-ctr")


if __name__ == "__main__":
    unittest.main()
