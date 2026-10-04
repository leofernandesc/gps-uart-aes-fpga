`timescale 1ns/1ps
`default_nettype none

// Original byte API retained; adds tx_ready and rx_framing_error.
// Production configuration: DE10-Lite, 50 MHz, 9600 baud, 8N1.
module uart_top #(
    parameter integer CLK_FREQ  = 50_000_000,
    parameter integer BAUD_RATE = 9600
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output wire       tx,
    output wire       tx_busy,
    output wire       tx_done,
    output wire       tx_ready,
    input  wire       rx,
    output wire [7:0] rx_data,
    output wire       rx_done,
    output wire       rx_framing_error
);
    localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;
    wire rst_core;

    reset_sync reset_inst (.clk(clk), .arst(rst), .rst(rst_core));
    assign tx_ready = !rst_core && !tx_busy;

    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) tx_inst (
        .clk(clk), .rst(rst_core), .tx_start(tx_start), .tx_data(tx_data),
        .tx(tx), .tx_busy(tx_busy), .tx_done(tx_done)
    );

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) rx_inst (
        .clk(clk), .rst(rst_core), .rx(rx), .rx_data(rx_data),
        .rx_done(rx_done), .rx_framing_error(rx_framing_error)
    );
endmodule

`default_nettype wire
