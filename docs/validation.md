# Verification coverage

The repository separates functional verification, implementation analysis,
and physical evidence. A pass in one category does not imply a pass in another.

| Layer | Command or evidence | What it checks |
| --- | --- | --- |
| AES-128 | make aes | AES core and transforms against independent known-answer vectors |
| AES-CTR | make ctr | Counter construction, byte ordering, partial blocks, stalls, exhaustion, and recovery |
| UART/FIFO | make uart and make bridge | 8N1 framing, handshakes, FIFO ordering, overflow and reset behavior |
| Integrated stream | make integration | Baseline and AES-CTR paths, serial TX decoding, byte counts, pause/error cases |
| Production-rate NMEA fixture | make integration-gps | Public 309-byte fixture at 50 MHz/9600 in both elaborations |
| Host software | make pc | Binary capture, context validation, independent decryption, comparison, and NMEA validation |
| Quartus | make baseline-fpga and make secure-fpga | Device fit, generated SOF, and timing audit; no board programming |
| Physical live GPS | AD2 capture plus CP2102 comparison | Simultaneous GPS/FPGA sampling and independent host-side recovery |

The AES test set contains 866 comparisons: 284 CAVP vectors, six published
examples, and 576 deterministic synthetic vectors. This is regression evidence,
not formal NIST CAVP or FIPS certification.

The selected post-fit and live-capture outcomes are summarized in
[results.md](results.md). A byte comparison and NMEA validation answer
different questions: the former tests transport transparency; the latter
checks sentence syntax and checksums.
