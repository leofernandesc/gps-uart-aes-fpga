`timescale 1ns/1ps
`default_nettype none

// Capacity study only. All non-clock ports are virtual; no board pinout/SOF.
// 48 MHz is a provisional oscillator assumption, not a verified board clock.
module capacity_top #(
    parameter integer ENABLE_AES = 1
) (
    input wire clk,
    input wire reset_n,
    input wire rx,
    output wire tx,
    output wire [9:0] status
);
    de10_lite_uart_ctr_top #(
        .ENABLE_AES (ENABLE_AES),
        .CLK_FREQ (48_000_000)
    ) implementation (
        .MAX10_CLK1_50 (clk), .KEY0_N (reset_n),
        .UART_RX (rx), .UART_TX (tx), .LEDR (status)
    );
endmodule

`default_nettype wire
