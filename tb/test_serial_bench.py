"""Tests for the one-adapter full-duplex CP2102 bench host."""
import hashlib
import json
import os
from pathlib import Path
import pty
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/serial_bench.py"


class SerialBenchTests(unittest.TestCase):
    stimulus = bytes.fromhex("55 A5 00 FF 3C")

    def _run_fake_fpga(self, mode, context, registry=None, trials=4):
        master, slave = pty.openpty()
        port = os.ttyname(slave)
        received = bytearray()
        stop = threading.Event()

        def responder():
            try:
                while not stop.is_set() and len(received) < len(self.stimulus) * trials:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    received.extend(chunk)
                    if mode == "baseline":
                        response = chunk
                    else:
                        from scripts.ctr_vectors import crypt
                        response = crypt(
                            bytes.fromhex(context["key_hex"]),
                            bytes.fromhex(context["nonce_hex"]),
                            context["initial_counter"],
                            bytes(received),
                        )[-len(chunk):]
                    os.write(master, response)
            except OSError:
                pass

        worker = threading.Thread(target=responder, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory(prefix="serial-bench-") as directory:
                directory = Path(directory)
                context_path = directory / "context.json"
                context_path.write_text(json.dumps(context), encoding="utf-8")
                output = directory / "received.bin"
                report = directory / "report.json"
                command = [
                    sys.executable, str(SCRIPT), "run", "--port", port,
                    "--context", str(context_path), "--received", str(output),
                    "--report", str(report), "--trials", str(trials),
                    "--response-guard", "0.002", "--interval", "0.001",
                ]
                if registry:
                    command += ["--registry", str(registry)]
                completed = subprocess.run(command, cwd=ROOT, text=True,
                                           capture_output=True, timeout=5)
                self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
                result = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["received_bytes"], len(output.read_bytes()))
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertEqual(report.stat().st_mode & 0o777, 0o600)
                return result
        finally:
            stop.set()
            os.close(slave)
            os.close(master)
            worker.join(timeout=1)

    def test_baseline_full_duplex_known_vector(self):
        context = {
            "schema": 1,
            "context_id": "baseline-test",
            "mode": "baseline",
            "bytes": len(self.stimulus) * 4,
        }
        result = self._run_fake_fpga("baseline", context)
        self.assertEqual(result["comparison"]["recovered_sha256"],
                         result["comparison"]["reference_sha256"])

    def test_secure_full_duplex_known_vector(self):
        context = {
            "schema": 1,
            "context_id": "secure-test",
            "mode": "aes-128-ctr",
            "bytes": len(self.stimulus) * 4,
            "key_hex": "000102030405060708090a0b0c0d0e0f",
            "nonce_hex": "101112131415161718191a1b",
            "initial_counter": 0,
        }
        context["key_sha256"] = hashlib.sha256(
            bytes.fromhex(context["key_hex"])
        ).hexdigest()
        with tempfile.TemporaryDirectory(prefix="serial-bench-registry-") as directory:
            registry = Path(directory) / "registry.json"
            registry.write_text(json.dumps({
                "schema": 1,
                "contexts": [{
                    "context_id": context["context_id"],
                    "key_sha256": context["key_sha256"],
                    "nonce_hex": context["nonce_hex"],
                    "initial_counter": 0,
                    "bytes": context["bytes"],
                }],
            }), encoding="utf-8")
            result = self._run_fake_fpga("secure", context, registry)
            self.assertEqual(result["comparison"]["recovered_sha256"],
                             result["comparison"]["reference_sha256"])

    def test_baseline_gps_replay(self):
        payload = b"$GPS\x00\xff\r\n"
        master, slave = pty.openpty()
        port = os.ttyname(slave)
        stop = threading.Event()

        def responder():
            try:
                data = os.read(master, len(payload))
                if data == payload:
                    os.write(master, data)
            except OSError:
                pass

        worker = threading.Thread(target=responder, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory(prefix="serial-replay-") as directory:
                directory = Path(directory)
                input_path = directory / "input.bin"
                input_path.write_bytes(payload)
                context_path = directory / "context.json"
                context_path.write_text(json.dumps({
                    "schema": 1,
                    "context_id": "replay-test",
                    "mode": "baseline",
                    "bytes": len(payload),
                }), encoding="utf-8")
                output = directory / "received.bin"
                report = directory / "report.json"
                completed = subprocess.run([
                    sys.executable, str(SCRIPT), "replay", "--port", port,
                    "--input", str(input_path), "--context", str(context_path),
                    "--received", str(output), "--report", str(report),
                    "--response-guard", "0.002",
                ], cwd=ROOT, text=True, capture_output=True, timeout=5)
                self.assertEqual(completed.returncode, 0,
                                 completed.stderr + completed.stdout)
                result = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(result["operation"], "gps-replay")
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(output.read_bytes(), payload)
        finally:
            stop.set()
            os.close(slave)
            os.close(master)
            worker.join(timeout=1)


if __name__ == "__main__":
    unittest.main()
