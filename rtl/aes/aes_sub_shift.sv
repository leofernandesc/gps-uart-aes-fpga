`timescale 1ns/1ps
`default_nettype none

// FIPS byte 0 is state_in[127:120]; state[r,c] = byte[4*c+r].
module aes_sub_shift (input wire [127:0] state_in, output wire [127:0] state_out);
    wire [127:0] substituted;
    genvar i, r, c;
    generate
        for (i = 0; i < 16; i = i + 1) begin : substitute
            aes_sbox sbox_inst (.data_in(state_in[127-8*i -: 8]),
                                .data_out(substituted[127-8*i -: 8]));
        end
        for (c = 0; c < 4; c = c + 1) begin : column
            for (r = 0; r < 4; r = r + 1) begin : row
                assign state_out[127-8*(4*c+r) -: 8] = substituted[127-8*(4*((c+r)%4)+r) -: 8];
            end
        end
    endgenerate
endmodule

`default_nettype wire
