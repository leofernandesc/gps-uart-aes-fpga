# FPGA-Based Secure GPS Data Acquisition and Transmission Using UART and AES-128-CTR

**Leonardo Fernandes Cavalcante**, **Edgard Luciano Oliveira Silva**<br>
Working draft for BTSym'26. Scope: u-blox NEO-M8N, DE10-Lite/MAX 10, 50 MHz
and 38400/8N1. Physical tests validate GPS acquisition and baseline forwarding,
as well as a live GPS-to-AES-CTR path with independent PC recovery.

## Abstract

GPS receivers commonly expose navigation data through an asynchronous serial
interface, which provides no confidentiality. This work implements and
evaluates two UART–FIFO datapaths on a DE10-Lite/MAX 10: a baseline forwarder
and a secure variant with AES-128-CTR. Both use a 50 MHz clock, 38400/8N1 UART
and a 1,024-byte FIFO. Physical tests captured NEO-M8N data and validated NMEA
sentences on the baseline path. In P13, 8,192 bytes from a live GPS stream were
encrypted by the FPGA, captured at the UART output and independently recovered
on the PC; 127 complete NMEA sentences passed checksum validation. A separate
32,768-byte stored-data replay passed in both variants. Quartus post-fit
analysis reports 331 logic elements and 212 registers for the baseline, versus
5,591 logic elements and 913 registers for the secure design. Minimum Fmax is
117.56 and 92.61 MHz, respectively, both above the 50 MHz operating clock.
The synthetic replay of the 309-byte public NMEA fixture at RTL had no
divergence or FIFO overflow and reached one-byte maximum FIFO occupancy. The
paper distinguishes simulation, implementation and physical results.

**Keywords:** FPGA, GPS, UART, AES-128-CTR, embedded security, reconfigurable
hardware.

## 1. Introduction

Navigation receivers are frequently integrated into embedded systems through
low-cost asynchronous serial links. NMEA sentences are easy to transport and
inspect, but the UART interface provides neither confidentiality nor protection
against modification. In applications where position information is sensitive,
adding a cryptographic layer must be evaluated together with the resource and
timing constraints of the communication path.

This work investigates a hardware architecture for secure serial GPS
data transmission. The design receives bytes through a UART connected to a
GPS-oriented input, stores them in a synchronous FIFO, optionally applies
AES-128-CTR, and emits the resulting bytes through a second UART stream. The
same RTL datapath is elaborated in two configurations so that the cost of the
cryptographic block can be isolated from the cost of the communication system.

The contributions are:

1. a byte-oriented UART–FIFO–AES-CTR integration designed for a fixed
   50 MHz, 38400 baud, 8N1 operating point;
2. separate baseline and secure elaborations for a DE10-Lite/MAX 10 target;
3. an independent PC oracle and reproducible NMEA replay for checking the
   bytes observed on the serial output; and
4. a quantitative comparison of post-fit resources, timing, FIFO occupancy and
   RTL end-to-end latency.

AES-CTR is used here to provide confidentiality. It does not provide message
authentication, integrity, replay protection or GNSS spoofing protection; these
limitations are part of the system definition and are discussed explicitly.

## 2. Proposed architecture

### 2.1 System datapath

The system is evaluated in two elaborated forms:

```text
GPS-oriented UART input
          |
       UART RX
          |
       FIFO 1024 B
          |
   +------+------+
   |             |
 baseline     AES-128-CTR
   |             |
   +------+------+
          |
       UART TX
          |
       PC receiver
```

The baseline removes the AES modules at elaboration time. It is therefore a
direct UART-plus-FIFO reference rather than a runtime bypass of the secure
datapath. The secure variant inserts the CTR stream after a byte is read from
the FIFO. The bridge retains a synchronously-read FIFO byte until the next
stage accepts it, preventing a one-cycle `valid` pulse from being lost during a
UART pause.

### 2.2 UART and buffering

The fixed operating point is 50 MHz FPGA clock, 38400 baud and 8N1 framing. The
UART receiver synchronizes the asynchronous input and samples the frame at its
center. Valid bytes enter a 1,024-byte synchronous FIFO. Framing errors and
FIFO overflow invalidate the active capture and remain visible until an
explicit abort or reset.

The FIFO is intentionally placed before the cryptographic stage. This keeps the
communication interface independent from the AES latency and allows the
experiment to observe whether the cryptographic stage becomes a bottleneck.

### 2.3 AES-128-CTR

AES-128 operates on 128-bit blocks with a 128-bit key. In CTR mode, AES encrypts
the concatenation of a 96-bit nonce and a 32-bit counter; the resulting mask is
XORed with the data stream. The implemented adapter exposes the mask one byte
at a time and advances it only when the corresponding output byte is accepted.
The counter is blocked before wraparound, and a new nonce is required for a new
capture with the same key.

The key, nonce and initial counter are experiment parameters. The current
DE10-Lite wrapper applies them statically during elaboration/build; no runtime
key-provisioning protocol is claimed.

## 3. Experimental method

### 3.1 Verification levels

The evaluation separates four kinds of evidence:

1. **RTL functional verification:** UART, FIFO, AES, CTR and bridge testbenches
   exercise normal transfers, pauses, framing errors, overflow, cancellation,
   reset and counter exhaustion.
2. **Independent PC verification:** the testbench decodes the serial TX wire,
   while Python and `cryptography` recover the secure stream independently of
   internal RTL payload or mask signals. A separate capture validator checks
   complete CRLF-delimited NMEA sentences, ASCII, checksums and sentence
   length before a physical GPS file can become an experiment reference.
3. **Quartus implementation analysis:** baseline and secure projects are fitted
   separately for the MAX 10 device, and resources, Fmax and timing slacks are
   collected from post-fit reports; and
4. **Physical validation:** the UART waveform is observed with an Analog
   Discovery 2, serial traffic is checked through a CP2102 USB–UART adapter, and
   NEO-M8N captures are parsed for ASCII, CRLF, sentence length and checksums.

The full `make check` regression passes at the revised UART setting, including
independent AES/CTR vectors, baseline/secure integration, structural checks and
37 Python tests. Physical tests confirmed UART framing, the NEO-M8N-to-DE10-Lite
baseline path, and a live GPS-to-AES-CTR path with PC recovery. Stored-data
replays P09/P10 remain separate deterministic tests with the GPS disconnected.

### 3.2 Workloads and test conditions

The public application fixture contains five NMEA sentences (RMC, GGA, GSA,
GSV and TXT), valid checksums and CRLF transmission endings. Its total length
is 309 bytes. It is a synthetic/public replay of the expected GPS format, not a
physical capture.

The checked-in fixture is converted to the same CRLF byte stream expected from
the serial source. For physical captures, `scripts/gps_capture.py` records the
sentence count, sentence types, byte count and SHA-256 only after the raw file
passes the formal checks. This protects the comparison workflow from malformed
or line-ending-converted data, but it does not independently prove the
electrical origin of a file.

| Test | Clock/UART | Data | Purpose |
| --- | --- | ---: | --- |
| RTL regression | accelerated and 50 MHz/38400 | short and boundary streams | functional and fault coverage |
| Synthetic NMEA replay | RTL at 50 MHz/38400 | 309 bytes | production-clock application path |
| Physical GPS baseline | NEO-M8N and DE10-Lite at 38400/8N1 | 4,096-byte captures | acquisition, forwarding and NMEA validity |
| Live GPS secure | NEO-M8N, secure DE10-Lite and PC at 38400/8N1 | 8,192 bytes | physical AES-CTR path, PC recovery and NMEA validity |
| Stored GPS replay | DE10-Lite baseline/secure at 38400/8N1 | 4,096 and 32,768 bytes | byte preservation and independent CTR recovery |
| Quartus post-fit | 50 MHz constraint | UART + FIFO, with/without AES-CTR | resource/timing cost |

## 4. Results

### 4.1 Functional and serial replay results

The complete NMEA replay was processed by both elaborations at the production
50 MHz/38400 baud timing. The baseline output matched the input bytes. The secure
output was recovered with the independent AES-CTR context and matched the same
309-byte input.

| Metric | Baseline | Secure |
| --- | ---: | ---: |
| Replayed bytes | 309 | 309 |
| FIFO maximum occupancy | 1 byte | 1 byte |
| RX-valid to TX start | 80 ns | 80 ns |
| RX-valid to TX done | 260,480 ns | 260,480 ns |
| Input-frame start to TX start | 247,503 ns | 247,503 ns |
| Byte divergences | 0 | 0 after recovery |
| FIFO overflow | 0 | 0 |

The small FIFO occupancy in the production-clock replay indicates that the
serial source, rather than the AES stage, dominates the transfer rate for this
workload. This conclusion is limited to the tested fixed-rate RTL model and
must be checked again with a physical GPS stream.

These nominal values come from the production-clock RTL replay without
artificial TX stalls. They are not electrical measurements of a GPS or a board.

### 4.2 Physical FPGA results

The DE10-Lite UART waveform was checked with the Analog Discovery 2. In the
baseline forwarding test, the five-byte stimulus was decoded correctly
on both RX and TX; the measured separation between the RX and TX start edges was
about 247.5 µs, including UART reception and byte validation. This is a physical
interface observation, not an isolated AES latency measurement.

The GPS and longer-stream tests are summarized below. GPS-derived bytes were
kept in the private experiment directory and are not reproduced in this paper.

| Test | Physical procedure | Result |
| --- | --- | --- |
| P07 | Direct NEO-M8N capture; then live GPS → DE10-Lite baseline → PC, captured in a separate window | 4,096 bytes in each capture; NMEA validator passed on 66 reference and 67 forwarded sentences |
| P08 | Baseline replay of the 4,096-byte GPS reference | 3/3 repetitions exact; zero missing/extra bytes |
| P09 | Secure replay of the 4,096-byte GPS reference | Ciphertext differed from input; PC recovery matched all 4,096 bytes |
| P10 | Baseline and secure replay of a 32,768-byte GPS reference | Baseline matched all bytes; secure ciphertext recovered exactly; zero missing/extra bytes |
| P11 | Secure reset, consumed-context lockout and recovery with a fresh context | Both 5-byte secure transfers passed; post-use probe received no response as expected |
| P12 | Live GPS acquisition through the baseline bitstream | 8,192 bytes; 127 complete NMEA sentences passed validation |
| P13 | Live GPS → DE10-Lite secure bitstream → PC; offline CTR recovery | 8,192 ciphertext bytes captured and recovered; 127 complete NMEA sentences passed; LEDR6/LEDR7 (FIFO overflow/framing) remained off |

The fixed-length P07/P10 files end at arbitrary byte boundaries. The NMEA
validator retained the trailing partial fragments (18 and 21 bytes in P07;
15 bytes in the P10 reference) and validated the complete sentences separately.

The two P07 captures were acquired at different times while the GPS output was
changing, so their byte streams were not compared directly. P13 adds physical
evidence of simultaneous live GPS acquisition and AES-CTR processing: the
secure output was recovered independently on the PC and its 127 complete NMEA
sentences passed checksum validation. The fixed-length capture retained a
35-byte trailing partial sentence. P09/P10 remain stored-data replays with the
GPS disconnected. P13 did not capture an independent parallel copy of the raw
GPS input for direct byte-for-byte comparison; the NMEA checksums and FPGA
overflow/framing indicators provide separate validation evidence.

The CP2102 host observed transaction times of about 1.078 s for 4,096 bytes and
8.545–8.546 s for 32,768 bytes. These include the PC, Linux serial driver and
USB bridge; they are end-to-end bench timings, not FPGA or AES latency. The
first 32-KiB baseline attempt ended early at 5,732 bytes; the recorded passing
result is the subsequent replay with RX collection active during transmission.
Both records were retained, but only the completed replay is counted as a pass.

### 4.3 FPGA post-fit comparison

| Metric | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Logic elements | 331 | 5,591 | +5,260 (+1,589.12%) |
| Registers | 212 | 913 | +701 (+330.66%) |
| Memory bits | 8,192 | 8,192 | 0 |
| Pins | 14 | 14 | 0 |
| Minimum Fmax | 117.56 MHz | 92.61 MHz | −24.95 MHz (−21.22%) |
| Worst setup slack | 11.494 ns | 9.202 ns | positive |
| Worst hold slack | 0.103 ns | 0.105 ns | positive |
| Worst recovery slack | 13.962 ns | 13.390 ns | positive |
| Worst removal slack | 0.440 ns | 2.487 ns | positive |

Both configurations meet the 50 MHz clock constraint in all audited corners.
The secure variant uses 11.24% of the 49,760 available logic elements, compared
with 0.67% for the baseline. Its AES round datapath contains 16 parallel S-boxes
and four more for key expansion. The fit hierarchy attributes 4,160 logic
elements to these 20 instances, explaining much of the logic cost. Round-key
expansion is performed on demand, avoiding an eleven-key register bank.
The table uses the selected 30 September builds, with shared source hashes,
seed and constraints checked; see [the metrics report](metricas-fpga-2026-09-30.md).
Each secure experiment provisions a fresh context; a different static context
can change synthesis and placement, so this table identifies one selected pair
rather than assigning its counts to every bitstream used in the campaign.

## 5. Discussion and limitations

The results show a clear implementation trade-off: AES-128-CTR increases logic
and register use and reduces post-fit Fmax, while both variants meet the same
50 MHz operating constraint. The 309-byte synthetic RTL replay reached a
maximum FIFO occupancy of one byte. Physical replays of 4,096 and 32,768 bytes
passed for both baseline and secure configurations, with independent recovery
of the secure payload. Similar host-observed transaction times for baseline and
secure are consistent with the fixed serial/host path dominating these tests,
but do not isolate the FPGA cryptographic latency.

Physical GPS acquisition, baseline forwarding and live GPS-to-AES-CTR operation
are demonstrated at the selected operating point. In P13, LEDR6 and LEDR7
remained off, indicating no sticky FIFO-overflow or UART-framing error during
the run. The 35-byte trailing fragment is due to the fixed capture limit, not a
reported framing error. AES-CTR does not authenticate data; an authenticated
mode or separate integrity mechanism would be required for a complete secure
telemetry protocol.

## 6. Evidence limits

The physical campaign used one DE10-Lite/MAX 10 board and one GPS module. P13
demonstrates live GPS-to-AES-CTR operation, but did not capture a parallel raw
GPS input for direct byte-for-byte comparison against the ciphertext recovery.
Valid NMEA checksums do not establish that no complete sentences were lost.
The live captures lasted approximately 10–11 s at the host and do not establish
long-duration stability.
LEDR6/LEDR7 were observed off in P13; FIFO occupancy (LEDR8) was not recorded.
Host-reported serial durations include Linux and USB–UART effects, and Quartus
Power Analyzer was not used; therefore no FPGA-only latency or measured power
claim is made. The key and nonce are build-time parameters, not runtime-
provisioned secrets. The consumed-context lock survives KEY0 reset only while
the FPGA remains configured and powered. Reprogramming the same SOF or cycling
power can restore its initial counter; every new secure acquisition therefore
requires a fresh context and matching bitstream. Finally, AES-CTR offers confidentiality but no
authentication or integrity protection.

## 7. Conclusion

This work presents a DE10-Lite architecture for UART-based GPS data forwarding
with optional AES-128-CTR confidentiality. RTL checks and post-fit analysis
quantify functional behavior and implementation cost; physical tests validate
the NEO-M8N baseline path and demonstrate live secure GPS acquisition with
independent PC recovery and NMEA checksum validation. Host timings are not
interpreted as AES latency. Both implementations meet the 50 MHz timing
constraint, while the secure variant incurs substantially higher logic and
register use. Future work should add authenticated encryption or a separate
integrity mechanism for secure telemetry.

## Reproduction references

- [`docs/metricas-fpga-2026-09-30.md`](metricas-fpga-2026-09-30.md)
- [`docs/validacao-replay-nmea-2026-09-20.md`](validacao-replay-nmea-2026-09-20.md)
- [`docs/validacao-captura-nmea-2026-09-20.md`](validacao-captura-nmea-2026-09-20.md)
- [`docs/plano-de-testes.md`](plano-de-testes.md)
- [`docs/integracao-uart-ctr.md`](integracao-uart-ctr.md)
- [`scripts/fpga_metrics.py`](../scripts/fpga_metrics.py)
- [`scripts/gps_capture.py`](../scripts/gps_capture.py)
