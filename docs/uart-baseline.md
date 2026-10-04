# UART baseline contract

This document describes the UART block used by the integrated DE10-Lite
baseline and AES-CTR designs. The complete datapath is documented in
[integracao-uart-ctr.md](integracao-uart-ctr.md).

## Implementation

The UART uses the 50 MHz system clock with local RX and TX bit counters. The
production profile is 9600 baud, 8N1, with 5,208 system-clock cycles per bit.
The RX synchronizes its asynchronous input, validates the start bit near its
center, then samples data and stop bits at the configured bit interval. The
TX sends one start bit, eight data bits LSB-first, and one stop bit.

The receiver reports a byte only after a valid stop bit. A low stop bit raises
a framing-error pulse and discards that frame. There is no oversampling,
parity, RTS/CTS, or noise-voting filter.

## Interface

All internal control and data signals are synchronous to the 50 MHz clock.
The serial RX pin and external reset are asynchronous inputs handled by the
top-level synchronization logic.

| Signal | Contract |
| --- | --- |
| clk | 50 MHz system clock |
| rst | Active high; aborts frames in progress |
| tx_data[7:0] | Byte sampled when a request is accepted |
| tx_start | Request accepted when tx_ready is high |
| tx_ready | High when TX can accept a byte |
| tx_busy | High during frame transmission |
| tx_done | One-cycle pulse after the complete stop bit |
| tx | Idle high; start low; data LSB-first; one stop bit |
| rx_data[7:0] | Last byte accepted with rx_done |
| rx_done | One-cycle pulse after a valid frame |
| rx_framing_error | One-cycle pulse when the stop bit is invalid |

The TX does not queue requests. A pulse while busy is ignored; a request held
high until ready may be accepted again. Producers must follow the ready/valid
handshake.

The RX has no ready signal because a GPS receiver cannot be paused through this
interface. The integrated design writes accepted bytes to a synchronous FIFO
and records overflow and framing errors. These conditions invalidate the
affected capture.

## Reset and recovery

After reset or a framing error, the receiver waits for an idle-high interval
before accepting another frame. Reset aborts an incomplete TX frame and does
not report it as completed. This is a datapath contract, not a packet-recovery
protocol; the host must reject captures marked with reset, framing, or overflow.

For the AES-CTR path, a new acquisition uses a fresh key/nonce context. Reset
does not make nonce reuse safe.

The baseline/AES-CTR post-fit comparison and physical results are in
[results.md](results.md).
