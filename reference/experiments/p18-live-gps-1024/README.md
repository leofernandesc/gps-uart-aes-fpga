# Public P18 live-GPS test artifact

This explicitly authorized copy contains real coordinates and a consumed dedicated test key. Never reuse this key/nonce for an independent operational stream. No nonce registry is published.

From the repository root:

```bash
python3 scripts/publish_experiment.py verify --input reference/experiments/p18-live-gps-1024
```

The verification decrypts with an independent Python library, checks every byte, and validates NMEA checksums. The nonce is 96 bits; the counter is 32-bit big-endian, with its initial value recorded in test-context.json. This artifact contains the matched 1,024-byte live trial; the extended live result is summarized in docs/results.md.
