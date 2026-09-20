# FPGA-Based Secure GPS Data Acquisition and Transmission Using UART and AES-128-CTR

**Leonardo Fernandes Cavalcante**, **Edgard Luciano Oliveira Silva**<br>
Working draft for BTSym'26. Physical GPS and integrated-board results are
identified explicitly as pending where applicable.

## Abstract

GPS receivers commonly expose their navigation data through an asynchronous
serial interface, but the resulting byte stream is not confidential by itself.
This work presents a custom RTL architecture for acquiring NMEA-like GPS data
through a 9600 baud, 8N1 UART and applying AES-128 in counter mode (CTR) before
serial transmission. The design is organized as a common UART and FIFO path
with two elaborated variants: a baseline that forwards the received bytes and
a secure variant that inserts an AES-128-CTR byte stream between reception and
transmission. Both variants were synthesized and fitted for a DE10-Lite/MAX 10
target with a 50 MHz clock. Independent software verification was used to
compare the bytes observed at the serial output and to recover the secure
stream. A 309-byte public NMEA replay was also executed at the production
50 MHz/9600 baud timing, with no byte divergence or FIFO overflow. Quartus
post-fit reports show 342 logic elements and 215 registers for the baseline,
against 6,984 logic elements and 2,196 registers for the secure variant; the
minimum reported Fmax decreases from 132.61 MHz to 82.19 MHz, while both
variants remain above the 50 MHz operating clock. The physical acquisition of
data from the NEO-M8N and the integrated-board experiment remain the final
validation stage.

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
   50 MHz, 9600 baud, 8N1 operating point;
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

The fixed operating point is 50 MHz FPGA clock, 9600 baud and 8N1 framing. The
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
   internal RTL payload or mask signals.
3. **Quartus implementation analysis:** baseline and secure projects are fitted
   separately for the MAX 10 device, and resources, Fmax and timing slacks are
   collected from post-fit reports.

The current evidence does not replace the final physical experiment. The
integrated baseline/secure bitstreams still have to be programmed and tested on
the DE10-Lite, and the NEO-M8N input must be captured electrically.

### 3.2 Workloads and test conditions

The public application fixture contains five NMEA sentences (RMC, GGA, GSA,
GSV and TXT), valid checksums and CRLF transmission endings. Its total length
is 309 bytes. It is a synthetic/public replay of the expected GPS format, not a
physical capture.

| Test | Clock/UART | Data | Purpose |
| --- | --- | ---: | --- |
| RTL regression | accelerated and 50 MHz/9600 | short and boundary streams | functional and fault coverage |
| NMEA replay | 50 MHz/9600 | 309 bytes | production-clock application path |
| Quartus baseline | 50 MHz constraint | UART + FIFO | reference resources/timing |
| Quartus secure | 50 MHz constraint | UART + FIFO + AES-CTR | cryptographic overhead |

## 4. Results

### 4.1 Functional and serial replay results

The complete NMEA replay was processed by both elaborations at the production
50 MHz/9600 baud timing. The baseline output matched the input bytes. The secure
output was recovered with the independent AES-CTR context and matched the same
309-byte input.

| Metric | Baseline | Secure |
| --- | ---: | ---: |
| Replayed bytes | 309 | 309 |
| FIFO maximum occupancy | 2 bytes | 2 bytes |
| First RX to first TX | 169,269 cycles / 3.385 ms | 169,269 cycles / 3.385 ms |
| First RX to last TX | 16,236,274 cycles / 324.725 ms | 16,236,274 cycles / 324.725 ms |
| Byte divergences | 0 | 0 after recovery |
| FIFO overflow | 0 | 0 |

The small FIFO occupancy in the production-clock replay indicates that the
serial source, rather than the AES stage, dominates the transfer rate for this
workload. This conclusion is limited to the tested fixed-rate RTL model and
must be checked again with a physical GPS stream.

### 4.2 FPGA post-fit comparison

| Metric | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Logic elements | 342 | 6,984 | +6,642 (+1,942.11%) |
| Registers | 215 | 2,196 | +1,981 (+921.40%) |
| Memory bits | 8,192 | 8,192 | 0 |
| Pins | 14 | 14 | 0 |
| Minimum Fmax | 132.61 MHz | 82.19 MHz | −50.42 MHz (−38.02%) |
| Worst setup slack | 12.459 ns | 7.833 ns | positive |
| Worst hold slack | 0.102 ns | 0.111 ns | positive |
| Worst recovery slack | 15.341 ns | 12.724 ns | positive |
| Worst removal slack | 0.424 ns | 2.332 ns | positive |

Both configurations meet the 50 MHz clock constraint in all audited corners.
The secure variant has a substantial logic/register cost because the current
AES implementation stores round-key state and uses an iterative round
datapath. Its minimum Fmax remains above the selected operating frequency.

## 5. Discussion and limitations

The results show a clear trade-off. Adding AES-128-CTR increases the logic and
register count and reduces the post-fit Fmax, while the UART workload remains
far below the available FPGA timing margin. The 9600 baud link also makes the
communication interval much longer than the internal AES operations for the
tested stream, which explains the low FIFO occupancy.

The current evaluation has four important limitations. First, the NMEA input
used in RTL is a public synthetic replay and not a live NEO-M8N capture. Second,
the integrated baseline and secure designs have been compiled but still need a
physical DE10-Lite programming and serial-output test. Third, the Cyclone IV
comparison is not part of the current quantitative table because its exact
device, clock and pinout have not been confirmed. Finally, AES-CTR alone does
not authenticate the data; an authenticated mode or a separate integrity
mechanism would be required for a complete secure telemetry protocol.

## 6. Final validation plan

The remaining physical experiment is:

1. program the baseline bitstream and verify a known serial stream;
2. connect the NEO-M8N TX to the configured FPGA RX with common ground and
   confirmed logic levels;
3. record an independent GPS reference and compare the baseline output;
4. program the secure bitstream, record the ciphertext and recover it on the
   PC with a fresh registered nonce; and
5. repeat the test for a continuous interval, recording losses, framing errors,
   FIFO overflow, latency and reset recovery.

The physical results should replace or extend Section 4 without changing the
RTL/PC methodology. Simulation, synthesis and post-fit analysis must remain
identified separately from those measurements.

## 7. Conclusion

This work defines and evaluates a reusable FPGA architecture for serial GPS
data acquisition with optional AES-128-CTR confidentiality. The common RTL
path makes the baseline and secure variants directly comparable, while the
independent PC checker and public NMEA replay make the experiment reproducible
before hardware access. The current DE10-Lite results quantify the cost of the
cryptographic stage and demonstrate that the design meets the 50 MHz timing
requirement in post-fit analysis. Physical GPS acquisition and integrated-board
validation are the remaining steps before the manuscript can claim end-to-end
hardware operation.

## Reproduction references

- [`docs/metricas-fpga-2026-09-20.md`](metricas-fpga-2026-09-20.md)
- [`docs/validacao-replay-nmea-2026-09-20.md`](validacao-replay-nmea-2026-09-20.md)
- [`docs/plano-de-testes.md`](plano-de-testes.md)
- [`docs/integracao-uart-ctr.md`](integracao-uart-ctr.md)
- [`scripts/fpga_metrics.py`](../scripts/fpga_metrics.py)
