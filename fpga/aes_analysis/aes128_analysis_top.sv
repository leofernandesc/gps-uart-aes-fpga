`timescale 1ns/1ps
`default_nettype none

// Internal timing/area harness: virtual block ports, no GPS pinout.
// Boundary timing is deliberately deferred to the real integrated design.
// The only extra logic is the reset synchronizer. No device image is produced.
module aes128_analysis_top (
    input  wire clk,
    input  wire arst,
    input  wire key_load,
    input  wire [127:0] key_in,
    output wire key_ready,
    output wire key_valid,
    output wire key_done,
    input  wire start,
    input  wire [127:0] block_in,
    output wire block_ready,
    output wire busy,
    output wire done,
    output wire [127:0] ciphertext
);
    wire rst;
    reset_sync reset_inst (.clk(clk), .arst(arst), .rst(rst));
    aes128_core core_inst (.*);
endmodule

`default_nettype wire
