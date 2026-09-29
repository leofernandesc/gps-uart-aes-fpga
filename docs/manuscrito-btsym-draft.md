# FPGA-Based Secure GPS Data Acquisition and Transmission Using UART and AES-128-CTR

**Leonardo Fernandes Cavalcante**, **Edgard Luciano Oliveira Silva**<br>
Working draft for BTSym'26. Scope updated on 29 September: u-blox
NEO-M9N-00B-00, DE10-Lite/MAX 10 only, 50 MHz and 38400/8N1. Previous
measurements at 9600 baud are historical and are not reported as results for
the final operating point. Physical GPS results remain pending until captured.

## Abstract

GPS receivers commonly expose navigation data through an asynchronous serial
interface, which provides no confidentiality. This work evaluates a custom RTL
architecture that receives NMEA data through the u-blox NEO-M9N UART and
transmits it through a DE10-Lite FPGA. Two elaborated variants share a
50 MHz, 38400 baud, 8N1 UART and a 1,024-byte FIFO: a baseline forwards bytes,
while a secure variant inserts AES-128-CTR. The study combines independent
AES/CTR verification, a 309-byte public NMEA replay, Quartus post-fit resource
and timing analysis. The baseline uses 331 logic elements and 212 registers;
the secure design uses 5,603 logic elements and 913 registers. Minimum Fmax is
117.56 and 103.38 MHz, respectively, above the common 50 MHz operating clock.
The simulated NMEA replay had no byte divergence or FIFO overflow and reached
one-byte maximum FIFO occupancy. Physical M9N acquisition remains pending and
is not inferred from the synthetic replay.

**Keywords:** FPGA, GPS, UART, AES-128-CTR, embedded security, reconfigurable
hardware.

## 1. Introduction

Navigation receivers are frequently integrated into embedded systems through
low-cost asynchronous serial links. NMEA sentences are easy to transport and
inspect, but the UART interface provides neither confidentiality nor protection
against modification. In applications where position information is sensitive,
adding a cryptographic layer must be evaluated together with the resource and
timing constraints of the communication path.

This work investigates a compact hardware architecture for secure serial GPS
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

The evaluation separates three kinds of evidence:

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
   collected from post-fit reports.

The full `make check` regression passes at the revised UART setting, including
independent AES/CTR vectors, baseline/secure integration, structural checks and
36 Python tests. These results do not constitute a physical GPS run.

The current evidence does not replace the final physical experiment. The
integrated baseline/secure bitstreams must be built for 38400 and tested on the
DE10-Lite. The NEO-M9N input has not yet been captured electrically at this
operating point.

### 3.2 Workloads and test conditions

The public application fixture contains five NMEA sentences (RMC, GGA, GSA,
GSV and TXT), valid checksums and CRLF transmission endings. Its total length
is 309 bytes. It is a synthetic/public replay of the expected GPS format, not a
physical capture.

The checked-in fixture is converted to the same CRLF byte stream expected from
the serial source. For a future live capture, `scripts/gps_capture.py` records
the sentence count, sentence types, byte count and SHA-256 only after the raw
file passes the same formal checks. This protects the comparison workflow from
truncated or line-ending-converted references, but it does not prove the
electrical origin of the file.

| Test | Clock/UART | Data | Purpose |
| --- | --- | ---: | --- |
| RTL regression | accelerated and 50 MHz/38400 | short and boundary streams | functional and fault coverage |
| NMEA replay | 50 MHz/38400 | 309 bytes | production-clock application path |
| Quartus baseline | 50 MHz constraint | UART + FIFO | reference resources/timing |
| Quartus secure | 50 MHz constraint | UART + FIFO + AES-CTR | cryptographic overhead |

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

### 4.2 FPGA post-fit comparison

| Metric | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Logic elements | 331 | 5,603 | +5,272 (+1,592.75%) |
| Registers | 212 | 913 | +701 (+330.66%) |
| Memory bits | 8,192 | 8,192 | 0 |
| Pins | 14 | 14 | 0 |
| Minimum Fmax | 117.56 MHz | 103.38 MHz | −14.18 MHz (−12.06%) |
| Worst setup slack | 11.494 ns | 10.327 ns | positive |
| Worst hold slack | 0.103 ns | 0.102 ns | positive |
| Worst recovery slack | 13.962 ns | 13.416 ns | positive |
| Worst removal slack | 0.440 ns | 2.230 ns | positive |

Both configurations meet the 50 MHz clock constraint in all audited corners.
The secure variant has a substantial logic/register cost because the current
AES implementation uses on-demand round-key expansion and an iterative round
datapath. The table was regenerated from the 29 September 38400-baud Quartus
fits; see [the dated metrics report](metricas-fpga-2026-09-29.md).

## 5. Discussion and limitations

The results show a clear trade-off. Adding AES-128-CTR increases logic and
register use and reduces the post-fit Fmax, while both variants must meet the
same 50 MHz operating clock. At 38400 baud, a 10-bit 8N1 frame takes about
260.4 µs; the 309-byte RTL replay showed a maximum FIFO occupancy of one byte
in both variants. This is evidence for the simulated workload, not a claim
about every GPS configuration or a long-duration physical run.

The NMEA workload in the reproducible RTL test is a public synthetic replay,
not a live NEO-M9N capture. Physical DE10-Lite and GPS results at 38400 remain
pending and must be kept separate from simulation and Quartus implementation
data. Finally, AES-CTR alone does not authenticate data; an authenticated
mode or separate integrity mechanism would be required for a complete secure
telemetry protocol.

## 6. Final validation plan

The remaining physical experiment is:

1. rebuild and program the 38400/8N1 baseline and secure bitstreams;
2. repeat UART waveform/loopback and known-vector P03–P06 on the DE10-Lite;
3. verify the NEO-M9N breakout supply and I/O levels, then capture its UART;
4. validate complete NMEA sentences and preserve the private capture hash;
5. run direct GPS acquisition and a deterministic replay through baseline and
   secure; recover ciphertext on the PC with a fresh registered nonce; and
6. execute a continuous interval, recording bytes, framing, FIFO overflow and
   reset behavior. Any unperformed measurement remains explicitly pending.

The physical results should replace or extend Section 4 without changing the
RTL/PC methodology. Simulation, synthesis and post-fit analysis must remain
identified separately from those measurements.

## 7. Conclusion

This work defines and evaluates a reusable FPGA architecture for serial GPS
data acquisition with optional AES-128-CTR confidentiality. The common RTL
path makes the baseline and secure variants directly comparable, while the
independent PC checker and public NMEA replay make the experiment reproducible
before physical GPS acquisition. The 38400-baud DE10-Lite results quantify the
cost of the cryptographic stage and show both builds meet the 50 MHz timing
requirement in post-fit analysis. Physical M9N acquisition and end-to-end board
validation remain pending; they must precede any claim of physical GPS
operation.

## Reproduction references

- [`docs/metricas-fpga-2026-09-29.md`](metricas-fpga-2026-09-29.md)
- [`docs/validacao-replay-nmea-2026-09-20.md`](validacao-replay-nmea-2026-09-20.md)
- [`docs/validacao-captura-nmea-2026-09-20.md`](validacao-captura-nmea-2026-09-20.md)
- [`docs/plano-de-testes.md`](plano-de-testes.md)
- [`docs/integracao-uart-ctr.md`](integracao-uart-ctr.md)
- [`scripts/fpga_metrics.py`](../scripts/fpga_metrics.py)
- [`scripts/gps_capture.py`](../scripts/gps_capture.py)
