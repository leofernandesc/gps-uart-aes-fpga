`timescale 1ns/1ps
`default_nettype none

// Unencrypted bench bridge. rst must have synchronously released deassertion.
// tx_enable is an internal pause input; it never truncates an active TX frame.
// Errors latch until reset and invalidate the capture; new input is dropped
// on overflow, preserving the order and contents of bytes already queued.
module uart_bridge #(
    parameter integer CLKS_PER_BIT = 5208,
    parameter integer FIFO_DEPTH = 1024,
    parameter integer LEVEL_WIDTH = $clog2(FIFO_DEPTH + 1)
) (
    input  wire                   clk,
    input  wire                   rst,
    input  wire                   rx,
    input  wire                   tx_enable,
    output wire                   tx,
    output wire                   tx_busy,
    output wire                   rx_event,
    output wire                   tx_event,
    output reg                    overflow_sticky,
    output reg                    framing_sticky,
    output wire [LEVEL_WIDTH-1:0] fifo_level,
    output wire [LEVEL_WIDTH-1:0] fifo_high_water
);
    wire [7:0] rx_data, fifo_data;
    wire framing_error, fifo_overflow, fifo_valid, fifo_empty;
    wire unused_fifo_full;
    reg read_pending;
    wire read_request = tx_enable && !rst && !tx_busy && !read_pending && !fifo_empty;

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) rx_inst (
        .clk(clk), .rst(rst), .rx(rx), .rx_data(rx_data),
        .rx_done(rx_event), .rx_framing_error(framing_error)
    );
    sync_fifo #(.DEPTH(FIFO_DEPTH), .LEVEL_WIDTH(LEVEL_WIDTH)) fifo_inst (
        .clk(clk), .rst(rst), .wr_en(rx_event), .wr_data(rx_data),
        .rd_en(read_request), .rd_data(fifo_data), .rd_valid(fifo_valid),
        .empty(fifo_empty), .full(unused_fifo_full), .level(fifo_level),
        .high_water(fifo_high_water), .overflow(fifo_overflow)
    );
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) tx_inst (
        .clk(clk), .rst(rst), .tx_start(fifo_valid), .tx_data(fifo_data),
        .tx(tx), .tx_busy(tx_busy), .tx_done(tx_event)
    );

    // Reserve the TX for the synchronous FIFO response on the following edge.
    // Once requested, the byte is committed even if tx_enable then falls.
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            read_pending    <= 1'b0;
            overflow_sticky <= 1'b0;
            framing_sticky  <= 1'b0;
        end else begin
            if (read_request) read_pending <= 1'b1;
            if (fifo_valid) read_pending <= 1'b0;
            if (fifo_overflow) overflow_sticky <= 1'b1;
            if (framing_error) framing_sticky <= 1'b1;
        end
    end
endmodule

`default_nettype wire
