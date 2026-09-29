`timescale 1ns/1ps
`default_nettype none

// Bench-only continuity diagnostic. No UART decoder, FIFO, or AES is present.
// Copy the external RX pin directly to the external TX pin; LEDR0 confirms
// that the programmed MAX 10 is clocked.
module uart_wire_diag_top (
    input  wire MAX10_CLK1_50,
    input  wire UART_RX,
    output wire UART_TX,
    output wire LEDR0
);
    reg [25:0] heartbeat_counter = 26'd0;

    always @(posedge MAX10_CLK1_50)
        heartbeat_counter <= heartbeat_counter + 1'b1;

    assign LEDR0 = heartbeat_counter[25];
    assign UART_TX = UART_RX;
endmodule

`default_nettype wire
