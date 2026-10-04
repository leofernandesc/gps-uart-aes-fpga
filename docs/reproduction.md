# Reproduction and build guide

Commands in this guide run from the repository root. Generated logs, SOFs,
temporary contexts, and captures belong under the ignored build/ or
data/private/ directories.

## Software and RTL checks

Run the complete regression:

~~~bash
make check
~~~

Useful focused targets are:

~~~bash
make uart
make bridge
make aes
make ctr
make integration
make integration-gps
make pc
make paper-check
make manuscript-check
~~~

The make check target selects native tools when the required set is installed;
otherwise it uses the locally available HDL Docker image. The HDL runner does
not download dependencies. The full live-GPS capture requires the physical
board, GPS, AD2, and serial adapter; it is not emulated by the software
regression.

## Quartus builds

Install Quartus Prime Lite with MAX 10 support and make quartus_sh available
on PATH, or set QUARTUS_SH to its full path. Build each matched variant:

~~~bash
make baseline-fpga
make secure-fpga
~~~

The Makefile calls scripts/quartus_build.sh, which invokes
quartus_sh --flow compile, runs the timing audit, and stores outputs under
build/de10_lite/baseline/ or build/de10_lite/secure/. A successful build
creates a .sof; the script does not program the board.

In Quartus, .qpf identifies the project, .qsf selects sources, device,
top-level entity, and pin assignments, and .sdc constrains clocks and timing.
The .sof configures the FPGA's volatile SRAM through JTAG. The Programmer is
a separate operation; for example:

~~~bash
quartus_pgm -c 'USB-Blaster [1-3]' -m jtag \
  -o 'p;build/de10_lite/baseline/uart_baseline.sof'
~~~

Programming a .sof is not the same as creating a persistent flash image.
These project targets do not create or program a .pof.

To fit a private AES context into the AES-CTR build, create the context outside
the repository and pass its path:

~~~bash
CONTEXT_FILE=data/private/run/context.json make secure-fpga
~~~

Keys, nonces, nonce registries, and live GPS captures must remain private unless
an artifact has been explicitly reviewed and approved for release. A new
independent CTR stream must not reuse a key/nonce pair.

## Verify published metrics and article source

The selected post-fit report can be checked against its source and artifact
hashes when the original build directories are available:

~~~bash
make metrics
make manuscript-check
python3 scripts/manuscript_check.py --offline
~~~

The offline mode checks the published snapshot and tracked source hashes; it
does not rerun Quartus or validate build artifacts that are not present in a
clone.

Check the LNCS source, bibliography, and the archived submitted PDF:

~~~bash
make paper-check
python3 paper/check_source.py --pdf paper/submitted.pdf
~~~

PDF compilation requires the Springer llncs.cls class and a local Tectonic
installation. The checked-in PDF is the exact manuscript copy supplied for
submission; do not replace it by a newly compiled file without reviewing the
rendered pages and updating the archival copy intentionally.

## Live capture wiring

For the DE10-Lite, GPS TX connects to FPGA RX on V10; FPGA TX is W10. Connect
AD2 DIO0 to GPS TX and DIO2 to FPGA TX for simultaneous digital capture. Connect
CP2102 RXD to FPGA TX for the independent host copy, with common ground.
Disconnect CP2102 TXD during a GPS-live capture. Do not connect two TX outputs
together or apply 5 V to FPGA I/O. The full bench procedure and interpretation
are in [bancada.md](bancada.md) and
[analog-discovery-2-waveforms.md](analog-discovery-2-waveforms.md).
