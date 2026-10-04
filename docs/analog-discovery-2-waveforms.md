# Analog Discovery 2 acquisition

The AD2 was used in DigitalIn mode as a two-channel logic analyzer for
simultaneous observation of the GPS UART output and the FPGA UART output. It
was not used as a UART transmitter or as the host-side byte comparator.

## Digital wiring and settings

| AD2 input | Signal | DE10-Lite connection |
| --- | --- | --- |
| DIO0 | GPS TX | GPS TX / FPGA RX V10 |
| DIO2 | FPGA TX | W10 |
| GND | Signal reference | Common ground |

Use DigitalIn with both selected DIO lines as inputs. The live acquisition
reported in the paper used 200,000 samples/s and decoded UART at 9600/8N1.
Connect CP2102 RXD to W10 for an independent host-side copy; keep CP2102 TXD
disconnected during GPS-live acquisition.

DIO0/DIO2 are digital channels. CH1+/CH1− and CH2+/CH2− are separate analog
oscilloscope inputs. If using the analog scope, connect each positive input to
the signal and its negative/reference to ground; select an input range suitable
for 0–3.3 V. Do not connect Wavegen outputs W1/W2 or the AD2 supply outputs to
the UART lines.

## Acquisition procedure

1. Connect common ground, then the GPS TX and FPGA TX observation leads.
2. Leave the GPS source inactive while AD2 and CP2102 are initialized.
3. Start the live capture with the intended context, build, rate, and baud.
4. Enable the GPS only after the tool prints READY.
5. Wait for completion; do not reset the FPGA or disturb the wiring.
6. Analyze the raw samples, UART frames, byte equality, and NMEA report.

The acquisition is invalid if the tool reports sample loss/corruption,
unexpected UART activity before READY, framing errors, false starts, or an
incomplete capture. The host copy is an independent observation of FPGA TX;
the AD2 provides concurrent GPS/FPGA sampling.

The capture command accepts an output directory that must not already exist.
See the command-line help with:

~~~bash
python3 scripts/ad2_live_capture.py record --help
python3 scripts/ad2_live_capture.py analyze --help
~~~

WaveForms' analog scope can be used to inspect voltage and bit timing, but a
screen image alone does not establish byte-exact recovery. The manuscript's
live comparison uses decoded digital samples plus independent host-side
decryption and byte comparison.
