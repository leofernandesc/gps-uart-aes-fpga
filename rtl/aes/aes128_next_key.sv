`timescale 1ns/1ps
`default_nettype none

// One AES-128 key-expansion step: RotWord/SubWord/Rcon, then four XOR words.
module aes128_next_key (
    input wire [127:0] current_key,
    input wire [7:0] rcon,
    output wire [127:0] next_key
);
    wire [31:0] rotated = {current_key[23:0], current_key[31:24]};
    wire [31:0] substituted;
    genvar i;
    generate
        for (i = 0; i < 4; i = i + 1) begin : word_byte
            aes_sbox sbox_inst (.data_in(rotated[31-8*i -: 8]),
                                .data_out(substituted[31-8*i -: 8]));
        end
    endgenerate
    // Keep dependencies on separate word nets: neither simulator nor linter
    // needs to resolve apparent whole-bus feedback through next_key slices.
    wire [31:0] w0 = current_key[127:96] ^ substituted ^ {rcon, 24'd0};
    wire [31:0] w1 = current_key[95:64] ^ w0;
    wire [31:0] w2 = current_key[63:32] ^ w1;
    wire [31:0] w3 = current_key[31:0] ^ w2;
    assign next_key = {w0, w1, w2, w3};
endmodule

`default_nettype wire
