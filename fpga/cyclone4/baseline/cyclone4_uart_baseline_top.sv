`timescale 1ns/1ps
`default_nettype none

module cyclone4_uart_baseline_top #(
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
    cyclone4_uart_ctr_top #(
        .ENABLE_AES      (0),
        .CLK_FREQ        (48_000_000),
        .CONTEXT_KEY     (CONTEXT_KEY),
        .CONTEXT_NONCE   (CONTEXT_NONCE),
        .CONTEXT_COUNTER (CONTEXT_COUNTER)
    ) implementation (
        .CLOCK_48 (CLOCK_48),
        .RESET_N  (RESET_N),
        .UART_RX  (UART_RX),
        .UART_TX  (UART_TX),
        .LED       (LED)
    );
endmodule

`default_nettype wire
