# Project documentation

The repository contains a completed FPGA prototype and the materials needed to
inspect or reproduce its checks. Start here, then use the focused technical
documents below.

## Project and results

- [Architecture](arquitetura.md): datapath, matched designs, and system scope.
- [Experimental results](results.md): selected Quartus metrics and live GPS
  captures, with the limits of each result.
- [Reproduction guide](reproduction.md): software checks, Quartus builds, and
  the submitted paper checks.

## RTL and host tools

- [AES-128 core](aes128.md): interface, byte order, latency, and test coverage.
- [AES-CTR stream adapter](ctr.md): counter construction and byte handshakes.
- [UART/FIFO/AES integration](integracao-uart-ctr.md): buffering, flow control,
  error flags, and reset behavior.
- [PC capture and comparison](captura-pc.md): binary capture, NMEA checks, and
  context handling.

## Hardware setup

- [DE10-Lite bench](bancada.md): pin mapping, electrical precautions, and
  simultaneous capture wiring.
- [CP2102 serial bench](cp2102-serial-bench.md): host-side known-vector and
  replay tests.
- [Analog Discovery 2](analog-discovery-2-waveforms.md): digital-input capture
  setup and interpretation.
- [UART baseline contract](uart-baseline.md): UART timing and interface.

## Article

- [Submitted PDF](../paper/submitted.pdf)
- [LNCS source](../paper/main.tex)
- [Bibliography](../paper/references.bib)
