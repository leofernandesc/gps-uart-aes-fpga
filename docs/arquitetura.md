# Architecture

The evaluated platform is a DE10-Lite with a MAX 10 10M50DAF484C7G, a
50 MHz system clock, and a u-blox NEO-M8N serial output at 9600/8N1.

## Datapath

    GPS TX -> UART RX -> synchronous FIFO -> baseline bypass or AES-128-CTR
          -> UART TX -> CP2102 -> host

Both designs use the same board, clock, UART pins, FIFO depth, and timing
constraints. The baseline project elaborates without AES. The AES-CTR project
adds the cipher path between the FIFO and UART transmitter.

The FIFO absorbs short bursts and decouples UART reception from downstream
handshakes. It is not a substitute for flow control during sustained overload.
Sticky framing-error and overflow indicators invalidate an affected capture.

The AES core encrypts a 128-bit counter block built from a 96-bit nonce and a
32-bit big-endian counter. The resulting keystream is XORed with each input
byte. Counter exhaustion is detected; the implementation does not wrap to a
previous counter value. Key and nonce are static build parameters, not a
runtime provisioning protocol.

## Quartus projects

| Target | Top-level purpose | Output |
| --- | --- | --- |
| uart_scope | Periodic 0x55 TX and RX diagnostics for bench checks | build/de10_lite/uart_scope/ |
| baseline | UART RX, FIFO, and UART TX without AES | build/de10_lite/baseline/ |
| secure | UART RX, FIFO, AES-CTR, and UART TX | build/de10_lite/secure/ |
| aes_analysis | Isolated AES implementation analysis with virtual ports | build/quartus_aes/ |

The .qpf selects a Quartus project. The .qsf lists HDL sources, the target
device, top-level entity, and pin assignments. The .sdc describes timing
constraints. Testbenches are not included in the programmed design.

Use the reproducible build targets in [reproduction.md](reproduction.md).
Compilation and timing analysis produce a SOF but do not program the board.

## Live-capture observation

For simultaneous digital observation, AD2 DIO0 samples GPS TX and DIO2 samples
FPGA TX. The CP2102 RXD line independently observes FPGA TX. The host compares
the captured output with the concurrent GPS reference; in AES-CTR mode it first
decrypts the output with a separate software implementation.

The live experiment and selected Quartus results are summarized in
[results.md](results.md). The AD2/CP2102 wiring and electrical precautions are
in [bancada.md](bancada.md).

## Security properties

CTR mode provides confidentiality when the key is secret and a nonce is not
reused with that key. It does not authenticate data or detect replay. A
deployed system would need key provisioning, nonce lifecycle management, and
an authenticated construction or a separate message-authentication mechanism.
