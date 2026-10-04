"""Exercise the capture reader with an SDK double, without USB/hardware."""
from collections import deque
from ctypes import memmove
import json
import os
from pathlib import Path
import pty
import sys
import tempfile
import termios
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from ad2_live_capture import (CommonIdlePreflight, DigitalRecordReader, UARTDecoder, assess, configure_record_buffer,
                             open_record_device, record, sample_divider)
from build_manifest import digest
from context import create_context
from gps_fixture import load_replay
from test_live_campaign import waveform


class FakeDigitalIn:
    def __init__(self, batches=(), apply_buffer=True):
        self.batches = deque(batches)
        self.buffer_size = 4096
        self.maximum = 16384
        self.apply_buffer = apply_buffer
        self.pending_buffer = self.buffer_size
        self.current = (b"", 0, 0)
        self.starts = []
        self.all_copied = Event()

    def FDwfDigitalInBufferSizeInfo(self, handle, maximum):
        maximum._obj.value = self.maximum
        return 1

    def FDwfDigitalInBufferSizeGet(self, handle, size):
        size._obj.value = self.buffer_size
        return 1

    def FDwfDigitalInBufferSizeSet(self, handle, size):
        self.pending_buffer = size.value
        return 1

    def FDwfDigitalInConfigure(self, handle, reconfigure, start):
        self.starts.append(start.value)
        if reconfigure.value or start.value:
            if self.apply_buffer:
                self.buffer_size = self.pending_buffer
        return 1

    def FDwfDigitalInStatus(self, handle, read_data, state):
        self.current = self.batches.popleft() if self.batches else (b"", 0, 0)
        state._obj.value = 3
        return 1

    def FDwfDigitalInStatusRecord(self, handle, available, lost, corrupt):
        available._obj.value = len(self.current[0])
        lost._obj.value, corrupt._obj.value = self.current[1:]
        return 1

    def FDwfDigitalInStatusData2(self, handle, buffer, index, count):
        assert index.value == 0 and count.value == len(self.current[0])
        memmove(buffer, self.current[0], count.value)
        if not self.batches:
            self.all_copied.set()
        return 1


class FakeCaptureSDK(FakeDigitalIn):
    """Two input-only digital channels; serial traffic uses a real Linux PTY."""
    def __init__(self, payload, corrupt=0, apply_divider=True, startup_zero=False):
        super().__init__([(b"\x05" * 16384, 0, 0)] * 12)
        if startup_zero:
            self.batches[0] = (b"\x00" + b"\x05" * 16383, 0, 0)
        self.activate = Event()
        self.post = deque()
        if corrupt:
            self.post.append((b"", 0, corrupt))
        else:
            wire = waveform(payload, rate=100000000 / 156)
            wire = wire.translate(bytes(value * 5 if value < 2 else 0 for value in range(256)))
            for offset in range(0, len(wire), 16384):
                self.post.append((wire[offset:offset + 16384], 0, 0))
        self.divider = 1
        self.pending_divider = 1
        self.apply_divider = apply_divider
        self.closed = False
        self.configurations = [(16, 4096), (16, 8192), (16, 16384), (0, 32768)]
        self.config_enumerated = False
        self.opened_config = None

    def FDwfDigitalInConfigure(self, handle, reconfigure, start):
        if (reconfigure.value or start.value) and self.apply_divider:
            self.divider = self.pending_divider
        return super().FDwfDigitalInConfigure(handle, reconfigure, start)

    def FDwfDigitalInStatus(self, handle, read_data, state):
        if not self.batches and self.activate.is_set() and self.post:
            self.batches, self.post = self.post, deque()
        return super().FDwfDigitalInStatus(handle, read_data, state)

    def FDwfEnum(self, kind, devices):
        devices._obj.value = 1
        return 1

    def FDwfEnumConfig(self, index, count):
        self.config_enumerated = True
        count._obj.value = len(self.configurations)
        return 1

    def FDwfEnumConfigInfo(self, index, info, value):
        assert self.config_enumerated, "SDK requires configuration enumeration first"
        value._obj.value = self.configurations[index.value][{4: 0, 9: 1}[info.value]]
        return 1

    def FDwfDeviceConfigOpen(self, index, configuration, handle):
        self.opened_config = configuration.value
        self.maximum = self.configurations[configuration.value][1]
        handle._obj.value = 1
        return 1

    def FDwfEnumDeviceType(self, index, device, revision):
        device._obj.value, revision._obj.value = 3, 3
        return 1

    def FDwfDigitalIOInputStatus(self, handle, inputs):
        inputs._obj.value = 5
        return 1

    def FDwfDigitalInInternalClockInfo(self, handle, clock):
        clock._obj.value = 100000000
        return 1

    def FDwfDigitalInDividerSet(self, handle, divider):
        self.pending_divider = divider.value
        return 1

    def FDwfDigitalInDividerGet(self, handle, divider):
        divider._obj.value = self.divider
        return 1

    def FDwfDigitalOutEnableSet(self, handle, channel, enable):
        assert enable.value == 0, "capture must never enable AD2 outputs"
        return 1

    def FDwfDigitalIOOutputEnableSet(self, handle, mask):
        assert mask.value == 0, "capture must remain input-only"
        return 1

    def FDwfDeviceClose(self, handle):
        self.closed = True
        return 1

    def __getattr__(self, name):
        if name in {"FDwfDeviceAutoConfigureSet", "FDwfDigitalOutConfigure",
                    "FDwfDigitalIOConfigure", "FDwfDigitalIOStatus",
                    "FDwfDigitalInAcquisitionModeSet", "FDwfDigitalInSampleFormatSet",
                    "FDwfDigitalInTriggerSourceSet", "FDwfDigitalInTriggerPositionSet"}:
            return lambda *args: 1
        raise AttributeError(name)


class DigitalRecordReaderTests(unittest.TestCase):
    def test_startup_zero_requires_full_idle_and_preserves_absolute_offsets(self):
        for rate in (200000, 100000000 / 156):
            for size in (28, 4096, 16384):
                with self.subTest(rate=rate, size=size):
                    report = {}
                    gate = CommonIdlePreflight(rate, 9600, 2, report)
                    wire = b"\x00" + b"\x05" * (gate.warmup_limit + gate.idle_target - 1)
                    decoder = UARTDecoder(rate)
                    decoder.offset = gate.warmup_limit
                    for offset in range(0, len(wire) - 1, size):
                        decoder.feed(gate.feed(wire[offset:min(offset + size, len(wire) - 1)]))
                    self.assertFalse(gate.ready, "warmup cannot count toward verified idle")
                    decoder.feed(gate.feed(wire[-1:]))
                    self.assertTrue(gate.ready)
                    self.assertEqual(report["instrument_warmup_non_idle_samples"], 1)
                    self.assertEqual(report["verified_common_idle_samples"], gate.idle_target)
                    self.assertEqual(decoder.offset, len(wire))
                    decoder.feed(waveform(b"$", rate=rate))
                    self.assertEqual(decoder.data, b"$")
                    self.assertGreaterEqual(decoder.starts[0], len(wire))

    def test_early_uart_and_low_after_warmup_still_fail(self):
        for bit in (0, 2):
            gate = CommonIdlePreflight(200000, 9600, 2, {})
            other_high = 5 ^ (1 << bit)
            early = bytes(value | other_high for value in waveform(b"$", bit=bit, rate=200000))
            with self.assertRaisesRegex(ValueError, "UART activity during"):
                gate.feed(early)
        for low in (0, 1, 4):
            gate = CommonIdlePreflight(200000, 9600, 2, {})
            with self.assertRaisesRegex(ValueError, "non-idle before READY"):
                gate.feed(b"\x05" * gate.warmup_limit + bytes([low]))

    def test_maximum_buffer_is_applied_and_verified(self):
        dwf = FakeDigitalIn()
        report = {}
        size = configure_record_buffer(dwf, 1, 641025.641025641, report)
        self.assertEqual(size, 16384)
        self.assertEqual(report["device_buffer_before_samples"], 4096)
        self.assertEqual(report["device_buffer_samples"], report["device_buffer_max_samples"])
        self.assertAlmostEqual(report["device_buffer_seconds"], 0.02555904)
        self.assertEqual(dwf.starts, [0], "configure while stopped before any readback")
        with self.assertRaisesRegex(ValueError, "did not apply"):
            configure_record_buffer(FakeDigitalIn(apply_buffer=False), 1, 1000000, {})

    def test_device_configuration_uses_largest_eligible_digital_buffer(self):
        from ctypes import c_int
        sdk = FakeCaptureSDK(b"")
        handle, report = c_int(), {}
        open_record_device(sdk, 0, handle, report)
        self.assertEqual(sdk.opened_config, 2)
        self.assertEqual(handle.value, 1)
        self.assertEqual(report["device_configuration_index"], 2)
        self.assertEqual(len(report["device_configurations"]), 4)
        sdk.configurations = [(0, 32768)]
        with self.assertRaisesRegex(ValueError, "no suitable"):
            open_record_device(sdk, 0, c_int(), {})

    def test_rate_rounding_preserves_decoder_minimum(self):
        # Preserve the prior 38.4-kbaud floor when explicitly requested.
        self.assertEqual(sample_divider(100000000, 614400, baud=38400), 162)
        for requested in (153600, 160000, 640000, 1000000, 2000000):
            divider = sample_divider(100000000, requested)
            self.assertGreaterEqual(100000000 / divider / 9600, 16)

    def test_reader_drains_while_consumer_is_paused_and_keeps_order(self):
        payloads = [bytes([n]) * (n + 4) for n in range(20)]
        dwf = FakeDigitalIn([(payload, 0, 0) for payload in payloads])
        # Reallocation and immutable copies also exercise reused SDK storage.
        reader = DigitalRecordReader(dwf, 1, buffer_size=4)
        with reader:
            self.assertTrue(dwf.all_copied.wait(1), "sampler depended on consumer progress")
            actual = [reader.read(timeout=1) for _ in payloads]
            self.assertEqual(actual, payloads)
        self.assertTrue(reader.finished.is_set())
        self.assertFalse(reader.thread.is_alive())
        self.assertEqual(dwf.starts, [1, 0])
        self.assertIsNone(reader.error)
        self.assertEqual(reader.stats["sampler_read_samples"], sum(map(len, payloads)))
        self.assertEqual(reader.stats["lost_samples"], 0)
        self.assertEqual(reader.stats["corrupt_samples"], 0)
        self.assertGreater(reader.stats["sampler_queue_high_water_chunks"], 1)

    def test_loss_or_corruption_aborts_without_accepting_bad_chunk(self):
        for lost, corrupt in ((0, 211), (17, 0), (3, 23)):
            with self.subTest(lost=lost, corrupt=corrupt):
                dwf = FakeDigitalIn([(b"good", 0, 0), (b"bad", lost, corrupt)])
                reader = DigitalRecordReader(dwf, 1, buffer_size=16)
                with reader:
                    self.assertTrue(reader.finished.wait(1))
                    with self.assertRaisesRegex(RuntimeError, "run invalid"):
                        reader.read()
                self.assertEqual(reader.stats["lost_samples"], lost)
                self.assertEqual(reader.stats["corrupt_samples"], corrupt)
                self.assertEqual(reader.stats["sampler_read_samples"], 4)
                self.assertEqual(reader.stats["sampler_fault_after_samples"], 4)
                self.assertEqual(reader.queue.get_nowait(), b"good")
                self.assertTrue(reader.queue.empty())
                self.assertEqual(dwf.starts, [1, 0])

    def test_full_host_queue_invalidates_instead_of_dropping_samples(self):
        reader = DigitalRecordReader(FakeDigitalIn([(b"a", 0, 0), (b"b", 0, 0)]),
                                     1, buffer_size=16, queue_chunks=1)
        with reader:
            self.assertTrue(reader.finished.wait(1))
            with self.assertRaisesRegex(RuntimeError, "queue full"):
                reader.read()
        self.assertTrue(reader.stats["sampler_host_queue_overflow"])
        self.assertEqual(reader.stats["lost_samples"], 0)
        self.assertEqual(reader.stats["corrupt_samples"], 0)
        self.assertEqual(reader.queue.get_nowait(), b"a")

    def test_record_complete_flow_and_corruption_after_ready(self):
        payload = load_replay()
        for corrupt, apply_divider, startup_zero, restore_error in (
                (0, True, False, False), (0, True, True, False),
                (211, True, False, False), (0, False, False, False), (0, True, False, True)):
            with self.subTest(corrupt=corrupt, apply_divider=apply_divider,
                              startup_zero=startup_zero, restore_error=restore_error), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                context_path = root / "context.json"
                create_context("baseline", len(payload), context_path, None)
                context = json.loads(context_path.read_text())
                build = root / "build"
                build.mkdir()
                (build / "context-binding.json").write_text(json.dumps({
                    "context_sha256": digest(context_path), "context_id": context["context_id"]}))
                master, slave = pty.openpty()
                sdk = FakeCaptureSDK(payload, corrupt=corrupt, apply_divider=apply_divider,
                                     startup_zero=startup_zero)
                ready = []

                def capture_print(*args, **kwargs):
                    if args and str(args[0]).startswith("READY:"):
                        ready.append(True)
                        os.write(master, payload)
                        sdk.activate.set()

                args = SimpleNamespace(confirm_source_inactive=True, confirm_txd_disconnected=True,
                    tx_dio=2, rate=640000, baud=9600, timeout=2, context=context_path, registry=None,
                    build=build, output=root / "capture", port=os.ttyname(slave), device_index=0)
                manifest = {"design": "baseline", "artifacts_sha256": {"uart_baseline.sof": "test"}}
                tcsetattr = termios.tcsetattr
                settings_calls = []

                def serial_settings(*values):
                    settings_calls.append(values)
                    if restore_error and len(settings_calls) == 2:
                        raise termios.error(5, "Input/output error")
                    return tcsetattr(*values)

                try:
                    with patch("ad2_live_capture.CDLL", return_value=sdk), \
                         patch("ad2_live_capture.verify", return_value=manifest), \
                         patch("ad2_live_capture.termios.tcsetattr", side_effect=serial_settings), \
                         patch("ad2_live_capture.print", side_effect=capture_print, create=True):
                        result = record(args)
                finally:
                    os.close(master)
                    os.close(slave)
                acquisition = json.loads((args.output / "acquisition.json").read_text())
                self.assertTrue(sdk.closed)
                self.assertEqual(sdk.opened_config, 2)
                if not apply_divider:
                    self.assertEqual(result, 1)
                    self.assertEqual(ready, [])
                    self.assertNotIn(1, sdk.starts, "must not start at an unverified sample rate")
                    self.assertEqual(acquisition["samples"], 0)
                    self.assertEqual(acquisition["sampling_divider"], 1)
                    self.assertTrue(any("did not apply sampling divider" in reason
                                        for reason in acquisition["invalid_reasons"]))
                    continue
                self.assertEqual(ready, [True])
                self.assertEqual(acquisition["sampling_divider"], 156)
                self.assertAlmostEqual(acquisition["sample_rate_hz"], 100000000 / 156)
                self.assertEqual(acquisition["corrupt_samples"], corrupt)
                self.assertEqual(acquisition["device_buffer_samples"], 16384)
                self.assertEqual(acquisition["lost_samples"], 0)
                self.assertTrue(acquisition["ready_idle_verified"])
                self.assertGreaterEqual(acquisition["verified_common_idle_samples"],
                                        acquisition["sample_rate_hz"] * .250)
                self.assertEqual(acquisition["instrument_warmup_non_idle_samples"], int(startup_zero))
                raw = (args.output / "samples.bin").read_bytes()
                self.assertEqual(len(raw), acquisition["samples"])
                self.assertEqual(raw[0], 0 if startup_zero else 5)
                if corrupt or restore_error:
                    self.assertEqual(result, 1)
                    self.assertEqual(acquisition["status"], "FAIL")
                    message = "Input/output error" if restore_error else "corrupt=211"
                    self.assertTrue(any(message in reason for reason in acquisition["invalid_reasons"]))
                else:
                    self.assertEqual(result, 0)
                    self.assertEqual(acquisition["status"], "CAPTURED")
                    streams = [(args.output / name).read_bytes() for name in
                               ("reference.bin", "cipher.bin", "cp2102.bin")]
                    self.assertEqual(streams, [payload] * 3)
                    assessment, recovered = assess(*streams, context, acquisition)
                    self.assertEqual(assessment["status"], "PASS")
                    self.assertEqual(recovered, payload)
                    self.assertGreaterEqual(acquisition["reference_frame_start_samples"][0],
                                            acquisition["ready_sample_offset"])


if __name__ == "__main__":
    unittest.main()
