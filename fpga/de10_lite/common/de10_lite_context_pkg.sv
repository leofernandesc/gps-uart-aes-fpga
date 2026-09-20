`timescale 1ns/1ps
`default_nettype none

// Public bring-up context. Real experiment contexts are generated privately
// in build/<board>/<design>/context_params.sv from a PC context JSON.
package de10_lite_context_pkg;
    localparam [127:0] CONTEXT_KEY =
        128'h000102030405060708090a0b0c0d0e0f;
    localparam [95:0] CONTEXT_NONCE =
        96'h101112131415161718191a1b;
    localparam [31:0] CONTEXT_COUNTER = 32'h00000001;
endpackage

`default_nettype wire
