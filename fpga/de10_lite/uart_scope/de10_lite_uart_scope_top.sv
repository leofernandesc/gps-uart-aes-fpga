`timescale 1ns/1ps
`default_nettype none

// 0x55 every 100 ms, 9600 8N1. KEY0 clears the test and restarts the timer.
// LED[7:0] = last RX byte; LED8 = byte received; LED9 = error since reset.
module de10_lite_uart_scope_top (
    input  wire       MAX10_CLK1_50,
    input  wire       KEY0_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [9:0] LEDR
);
    uart_scope #(.CLK_FREQ(50_000_000), .BAUD_RATE(9600)) scope_inst (
        .clk(MAX10_CLK1_50), .arst(!KEY0_N), .rx(UART_RX), .tx(UART_TX),
        .last_rx_data(LEDR[7:0]), .rx_seen(LEDR[8]), .error_sticky(LEDR[9])
    );
endmodule

`default_nettype wire
