`timescale 1ns/1ps
`default_nettype none

// Board wrapper for the ZRTech/WXEDA EP4CE6E22C8N candidate profile.
//
// The implementation is shared with the DE10-Lite comparison.  Only the
// board-facing clock, reset, serial pins and four active-low LEDs are adapted
// here.  The Cyclone IV board exposes four user LEDs in this profile, so the
// remaining diagnostics stay inside the common wrapper and can be observed by
// the serial test or by a future SignalTap build.
module cyclone4_uart_ctr_top #(
    parameter integer ENABLE_AES = 1,
    parameter integer CLK_FREQ = 48_000_000,
    parameter [127:0] CONTEXT_KEY =
        de10_lite_context_pkg::CONTEXT_KEY,
    parameter [95:0] CONTEXT_NONCE =
        de10_lite_context_pkg::CONTEXT_NONCE,
    parameter [31:0] CONTEXT_COUNTER =
        de10_lite_context_pkg::CONTEXT_COUNTER
) (
    input  wire       CLOCK_48,
    input  wire       RESET_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [3:0] LED
);
    wire [9:0] diagnostics;

    de10_lite_uart_ctr_top #(
        .ENABLE_AES      (ENABLE_AES),
        .CLK_FREQ        (CLK_FREQ),
        .CONTEXT_KEY     (CONTEXT_KEY),
        .CONTEXT_NONCE   (CONTEXT_NONCE),
        .CONTEXT_COUNTER (CONTEXT_COUNTER)
    ) implementation (
        .MAX10_CLK1_50 (CLOCK_48),
        .KEY0_N        (RESET_N),
        .UART_RX       (UART_RX),
        .UART_TX       (UART_TX),
        .LEDR          (diagnostics)
    );

    // The board LEDs are active-low.  Keep the first four common diagnostics:
    // heartbeat, active/acquisition, RX activity and TX activity.
    assign LED = ~diagnostics[3:0];
endmodule

`default_nettype wire
