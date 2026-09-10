`timescale 1ns/1ps
`default_nettype none

module aes_mix_columns (input wire [127:0] state_in, output wire [127:0] state_out);
    function automatic [7:0] xtime(input reg [7:0] a);
        xtime = {a[6:0], 1'b0} ^ (a[7] ? 8'h1b : 8'h00);
    endfunction
    genvar c;
    generate
        for (c = 0; c < 4; c = c + 1) begin : column
            wire [7:0] a = state_in[127-32*c -: 8];
            wire [7:0] b = state_in[119-32*c -: 8];
            wire [7:0] d = state_in[111-32*c -: 8];
            wire [7:0] e = state_in[103-32*c -: 8];
            wire [7:0] total = a ^ b ^ d ^ e;
            assign state_out[127-32*c -: 8] = a ^ total ^ xtime(a ^ b);
            assign state_out[119-32*c -: 8] = b ^ total ^ xtime(b ^ d);
            assign state_out[111-32*c -: 8] = d ^ total ^ xtime(d ^ e);
            assign state_out[103-32*c -: 8] = e ^ total ^ xtime(e ^ a);
        end
    endgenerate
endmodule

`default_nettype wire
