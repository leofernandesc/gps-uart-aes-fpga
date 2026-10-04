# DE10-Lite and GPS bench

This guide describes the physical connections used for the live GPS data-path
captures. Use 3.3 V-compatible logic and establish common ground before
connecting signal wires. Do not connect two TX outputs together.

## FPGA pin mapping

| Signal | DE10-Lite pin | Use |
| --- | --- | --- |
| UART RX | V10, JP1 position 1 | GPS TX or CP2102 TXD input |
| UART TX | W10, JP1 position 2 | CP2102 RXD and AD2 observation |
| Ground | JP1 ground, position 12 or 30 | Common signal reference |
| Clock | P11 | 50 MHz board clock |

Confirm connector orientation and board pinout before wiring. Never apply 5 V
to the FPGA I/O. The GPS carrier's supply requirements depend on the breakout;
the experimental breakout was operated at 3.3 V.

## Simultaneous live capture

| Source | Destination |
| --- | --- |
| GPS TX | FPGA RX V10 and AD2 DIO0 |
| FPGA TX W10 | AD2 DIO2 and CP2102 RXD |
| GPS, FPGA, AD2, CP2102 grounds | Common ground |
| CP2102 TXD | Disconnected during GPS-live capture |

The AD2 DIO0 and DIO2 pins are digital inputs. They are not the analog
oscilloscope inputs CH1+ and CH2+. A scope probe may observe the same signal
separately, but identify the connection type correctly in the acquisition
software.

For a UART replay from the PC, CP2102 TXD connects to FPGA RX V10 and CP2102
RXD connects to FPGA TX W10. Disconnect the GPS TX before connecting CP2102
TXD to avoid tying two outputs together.

## Capture sequence

1. Program the intended baseline or AES-CTR SOF and confirm the programmed
   project.
2. Keep the GPS source inactive while the acquisition tool arms the AD2 and
   CP2102. The tool prints READY after setup.
3. Enable the GPS source only after READY. Do not press reset during a capture.
4. Save the raw acquisition and comparison report to a new private output
   directory.
5. For AES-CTR, use the matching test context and independently decrypt the
   captured ciphertext before comparing it with GPS TX.
6. Check sample loss/corruption, framing errors, false starts, overflow and
   framing indicators, reset observations, byte counts, hashes, and NMEA
   checksums.

Use a new output path for every run. A captured byte count alone is not a
comparison pass. Keep raw GPS coordinates, private contexts, keys, and nonce
registries out of the repository unless a specific artifact is reviewed and
explicitly approved for publication.

See [reproduction.md](reproduction.md) for the capture software and
[results.md](results.md) for the evidence reported in the manuscript.
