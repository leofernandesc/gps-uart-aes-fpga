# AES-128-CTR for a live GPS UART stream

This project evaluates the hardware cost and data-path behavior of adding
AES-128-CTR to a live GPS serial stream on a DE10-Lite/MAX 10 FPGA. It contains
the RTL, simulation testbenches, Quartus projects, host-side verification tools,
selected experimental evidence, and the Springer LNCS manuscript.

The manuscript is reported by the authors as submitted. The exact submitted
PDF and its matching LaTeX source are included in [`paper/`](paper/).

## System

The evaluated paths share the same board, clock, UART, FIFO, and timing
constraints. AES-CTR is the only architectural difference.

    NEO-M8N GPS -> UART RX -> 1,024-byte FIFO -> [bypass | AES-128-CTR]
               -> UART TX -> CP2102 / host

For live trials, the Analog Discovery 2 sampled GPS TX and FPGA TX
simultaneously. The host independently checked the serial output and, for the
AES-CTR path, decrypted it before byte-by-byte comparison with the GPS reference.

## Results

The selected Quartus post-fit pair targets the MAX 10
10M50DAF484C7G at 50 MHz and 9600/8N1.

| Metric | Baseline | AES-CTR |
| --- | ---: | ---: |
| Logic elements | 347 (0.70%) | 5,655 (11.36%) |
| Registers | 216 | 917 |
| Memory | 8,192 bits | 8,192 bits |
| Minimum Fmax | 123.00 MHz | 95.07 MHz |
| Timing checks at 50 MHz | Pass | Pass |

The live-data results distinguish the matched pilots from the longer,
supplementary captures:

| Trial | Bytes checked | Outcome |
| --- | ---: | --- |
| Baseline, paired live capture | 1,024 | Exact GPS-to-FPGA forwarding; 24 valid NMEA sentences |
| AES-CTR, paired live capture | 1,024 | Exact recovery after decryption; 24 valid NMEA sentences |
| AES-CTR, extended live capture | 65,536 | Exact recovery; 1,112 valid NMEA sentences |
| Baseline, supplementary capture | 65,536 | Copies match byte-for-byte; strict NMEA validation rejects 0xEA at offset 127 |

The supplementary baseline run is evidence of byte transparency, not a clean
NMEA capture. The long AES-CTR run is not a repeated, symmetric reliability
campaign. Detailed values, hashes, and scope are in
[`docs/results.md`](docs/results.md).

## Reproduce the checks

From the repository root:

~~~bash
make check
make paper-check
make manuscript-check
python3 scripts/publish_experiment.py verify \
  --input reference/experiments/p18-live-gps-1024
~~~

`make check` runs the HDL regression and software tests. Quartus builds are
separate and do not program a board:

~~~bash
make baseline-fpga
make secure-fpga
~~~

See [`docs/reproduction.md`](docs/reproduction.md) for dependencies, build
outputs, and the distinction between compilation and JTAG programming.

## Security scope

CTR mode provides confidentiality but not integrity, authenticity, or replay
protection. The prototype loads its key and nonce as build parameters; it is an
experimental data path, not a production security protocol. The public P18
artifact intentionally includes a consumed test key and real GPS reference
data for reproducibility. Do not reuse its key or nonce.

## Repository map

- [`rtl/`](rtl/): UART, FIFO, AES-128, CTR, and integrated bridge.
- [`fpga/de10_lite/`](fpga/de10_lite/): Quartus projects, tops, pin assignments,
  and timing constraints.
- [`tb/`](tb/): HDL testbenches and Python tests.
- [`scripts/`](scripts/): build, capture, comparison, and verification tools.
- [`reference/`](reference/): public test vectors, GPS fixture, and selected
  live-capture artifact.
- [`docs/`](docs/): architecture, results, bench setup, and reproduction guide.
- [`paper/`](paper/): submitted Springer manuscript source and PDF.

See [`docs/README.md`](docs/README.md) for the documentation index.
