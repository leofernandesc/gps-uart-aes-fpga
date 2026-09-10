`timescale 1ns/1ps
`default_nettype none

// Single clock, synchronous read. rd_data is meaningful only with rd_valid.
// No reset on the RAM array/output: MAX 10 block RAM can be inferred.
// A simultaneous read frees space for a write even when initially full.
module sync_fifo #(
    parameter integer DEPTH = 1024,
    parameter integer WIDTH = 8,
    parameter integer LEVEL_WIDTH = $clog2(DEPTH + 1)
) (
    input  wire                   clk,
    input  wire                   rst,
    input  wire                   wr_en,
    input  wire [WIDTH-1:0]       wr_data,
    input  wire                   rd_en,
    output reg  [WIDTH-1:0]       rd_data,
    output reg                    rd_valid,
    output wire                   empty,
    output wire                   full,
    output reg  [LEVEL_WIDTH-1:0] level,
    output reg  [LEVEL_WIDTH-1:0] high_water,
    output reg                    overflow
);
    localparam integer ADDR_WIDTH = $clog2(DEPTH);
    reg [WIDTH-1:0] memory [0:DEPTH-1];
    reg [ADDR_WIDTH-1:0] wr_ptr, rd_ptr;
    wire pop = rd_en && !empty && !rst;
    wire push = wr_en && (!full || pop) && !rst;

    assign empty = (level == 0);
    assign full = (level == LEVEL_WIDTH'(DEPTH));

`ifndef SYNTHESIS
    initial begin
        if (DEPTH < 2 || (DEPTH & (DEPTH - 1)) != 0)
            $fatal(1, "sync_fifo DEPTH must be a power of two >= 2");
        if (LEVEL_WIDTH != $clog2(DEPTH + 1) || WIDTH < 1)
            $fatal(1, "sync_fifo invalid width");
    end
`endif

    // Nonblocking assignments specify old data on a full read/write collision.
    always @(posedge clk) begin
        if (push) memory[wr_ptr] <= wr_data;
        if (pop) rd_data <= memory[rd_ptr];
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            wr_ptr     <= '0;
            rd_ptr     <= '0;
            level      <= '0;
            high_water <= '0;
            rd_valid   <= 1'b0;
            overflow   <= 1'b0;
        end else begin
            rd_valid <= pop;
            overflow <= wr_en && !push;
            if (push) wr_ptr <= wr_ptr + 1'b1;
            if (pop) rd_ptr <= rd_ptr + 1'b1;
            case ({push, pop})
                2'b10: begin
                    level <= level + 1'b1;
                    if (level == high_water) high_water <= level + 1'b1;
                end
                2'b01: level <= level - 1'b1;
                default: ;
            endcase
        end
    end
endmodule

`default_nettype wire
