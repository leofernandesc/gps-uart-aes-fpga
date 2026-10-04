# Experimental results

The results below describe the selected DE10-Lite/MAX 10 implementation and
the physical captures reported in the manuscript. Evidence types are kept
separate: simulation, post-fit timing, and live hardware capture support
different claims.

## Matched Quartus builds

Both builds target device 10M50DAF484C7G at 50 MHz, 9600/8N1, with a
1,024-byte FIFO and the same timing constraints. The baseline elaborates
without AES; the AES-CTR build adds the encryption datapath.

| Post-fit metric | Baseline | AES-CTR | AES-CTR − baseline |
| --- | ---: | ---: | ---: |
| Logic elements | 347 (0.70%) | 5,655 (11.36%) | +5,308 |
| Registers | 216 | 917 | +701 |
| Memory bits | 8,192 | 8,192 | 0 |
| Pins | 14 | 14 | 0 |
| Minimum Fmax | 123.00 MHz | 95.07 MHz | −27.93 MHz |
| Worst setup slack | 11.870 ns | 9.481 ns | Positive in both |
| Worst hold slack | 0.102 ns | 0.089 ns | Positive in both |
| Worst recovery slack | 14.454 ns | 13.184 ns | Positive in both |
| Worst removal slack | 0.439 ns | 2.216 ns | Positive in both |

Both builds meet the 50 MHz operating constraint in the audited timing corners.
Fmax is a Quartus post-fit static timing result, not a frequency measured on
the board. The versioned snapshot
[selected post-fit JSON](evidence/de10-lite-postfit-9600-2026-09-30.json)
contains build provenance and SHA-256 hashes for the selected sources and
artifacts.

## Live GPS captures

The paired baseline and AES-CTR pilots each compared 1,024 bytes from a live
GPS acquisition. GPS TX and FPGA TX were sampled simultaneously by the AD2;
the CP2102 provided an independent host-side copy.

| Capture | Bytes | Result |
| --- | ---: | --- |
| Baseline, paired | 1,024 | GPS reference and FPGA output matched exactly; 24 complete NMEA sentences passed checksum validation |
| AES-CTR, paired | 1,024 | Independent decryption matched the GPS reference exactly; 24 complete NMEA sentences passed checksum validation |
| AES-CTR, extended | 65,536 | Decrypted stream matched the GPS reference; 1,112 complete NMEA sentences passed checksum validation |
| Baseline, supplementary | 65,536 | GPS reference, FPGA output, and CP2102 copy matched byte-for-byte; strict NMEA validation rejected a non-printable byte |

For the extended AES-CTR capture, the AD2 acquired 16,181,804 samples and
decoded 65,536 UART frames on each channel. It reported no lost or corrupt
samples, framing errors, or false starts. The operator observed the overflow
and framing indicators inactive and no reset during capture.

The ciphertext observed by AD2 and CP2102 has SHA-256:

    88c96353f03e826ef9fa12001f21bd656e5d70e277f31b256e78e16cb3037328

The GPS reference and independently recovered plaintext share SHA-256:

    84fc38de8c9fb9df25ce19b0489a6d73854ae07eb15876e2e01401c695f4bb2c

The supplementary baseline stream contained byte 0xEA at offset 127 in both
the GPS reference and all output copies. No bytes were missing or added, but
the strict NMEA validator rejected the stream. The cause of that byte was not
established; this run supports byte-transparent forwarding, not a clean NMEA
capture.

The 65,536-byte AES-CTR capture extends the live trial but is not a repeated,
balanced long-duration campaign: the matched baseline/AES-CTR comparison is
the pair of 1,024-byte captures.

## Public reproducibility artifact

The selected P18 artifact is in
[reference/experiments/p18-live-gps-1024/](../reference/experiments/p18-live-gps-1024/).
It contains the captured reference, ciphertext, recovered bytes, context, and
checksums required for independent verification. The artifact was explicitly
approved for public release and includes real GPS data and a consumed test key.
Never reuse its key/nonce for another stream.

Verify it from the repository root:

~~~bash
python3 scripts/publish_experiment.py verify \
  --input reference/experiments/p18-live-gps-1024
~~~

The 1 MiB stored-data replay was not part of the reported results.
