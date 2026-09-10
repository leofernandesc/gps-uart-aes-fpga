`timescale 1ns/1ps
`default_nettype none

module aes_components_tb;
    reg [7:0] data_in;
    wire [7:0] data_out;
    reg [127:0] state_in, current_key;
    reg [7:0] rcon;
    wire [127:0] shifted, mixed, next_key;
    aes_sbox sbox_inst (.*);
    aes_sub_shift shift_inst (.state_in(state_in), .state_out(shifted));
    aes_mix_columns mix_inst (.state_in(state_in), .state_out(mixed));
    aes128_next_key key_inst (.*);

    // Algebraic oracle, independent of the RTL S-box table and xtime shortcut.
    function automatic [7:0] multiply(input reg [7:0] a, input reg [7:0] b);
        reg [15:0] product;
        integer i;
        begin
            product = 0;
            for (i = 0; i < 8; i = i + 1)
                if (b[i]) product = product ^ ({8'd0, a} << i);
            for (i = 14; i >= 8; i = i - 1)
                if (product[i]) product = product ^ (16'h011b << (i - 8));
            multiply = product[7:0];
        end
    endfunction
    function automatic [7:0] algebra_sbox(input reg [7:0] a);
        reg [7:0] inverse, base, result;
        integer i;
        begin
            inverse = 1;
            base = a;
            for (i = 0; i < 8; i = i + 1) begin
                if ((254 >> i) & 1) inverse = multiply(inverse, base);
                base = multiply(base, base);
            end
            result = inverse ^ 8'h63;
            for (i = 1; i < 5; i = i + 1)
                result = result ^ ((inverse << i) | (inverse >> (8 - i)));
            algebra_sbox = result;
        end
    endfunction
    function automatic [127:0] matrix_mix(input reg [127:0] value);
        reg [7:0] a, b, c, d;
        integer col;
        begin
            for (col = 0; col < 4; col = col + 1) begin
                {a, b, c, d} = value[127-32*col -: 32];
                matrix_mix[127-32*col -: 32] = {
                    multiply(a,2) ^ multiply(b,3) ^ c ^ d,
                    a ^ multiply(b,2) ^ multiply(c,3) ^ d,
                    a ^ b ^ multiply(c,2) ^ multiply(d,3),
                    multiply(a,3) ^ b ^ c ^ multiply(d,2)};
            end
        end
    endfunction

    reg [127:0] keys [0:10];
    reg [127:0] random_state = 128'h52da643fb194074ca863db829cd5a61e;
    reg [127:0] expected_shift;
    integer n, r, c;
    initial begin
        keys[0] = 128'h2b7e151628aed2a6abf7158809cf4f3c;
        keys[1] = 128'ha0fafe1788542cb123a339392a6c7605;
        keys[2] = 128'hf2c295f27a96b9435935807a7359f67f;
        keys[3] = 128'h3d80477d4716fe3e1e237e446d7a883b;
        keys[4] = 128'hef44a541a8525b7fb671253bdb0bad00;
        keys[5] = 128'hd4d1c6f87c839d87caf2b8bc11f915bc;
        keys[6] = 128'h6d88a37a110b3efddbf98641ca0093fd;
        keys[7] = 128'h4e54f70e5f5fc9f384a64fb24ea6dc4f;
        keys[8] = 128'head27321b58dbad2312bf5607f8d292f;
        keys[9] = 128'hac7766f319fadc2128d12941575c006e;
        keys[10] = 128'hd014f9a8c9ee2589e13f0cc8b6630ca6;
        state_in = 0;
        current_key = keys[0];
        rcon = 1;
        for (n = 0; n < 256; n = n + 1) begin
            data_in = 8'(n);
            #1;
            if (data_out !== algebra_sbox(8'(n))) $fatal(1, "S-box byte %02x failed", n);
        end
        for (n = 1; n <= 10; n = n + 1) begin
            #1;
            if (next_key !== keys[n]) $fatal(1, "FIPS key expansion round %0d mismatch", n);
            current_key = next_key;
            rcon = multiply(rcon, 2);
        end
        // FIPS 197 Appendix B, first round, column-major byte representation.
        state_in = 128'h193de3bea0f4e22b9ac68d2ae9f84808;
        #1;
        if (shifted !== 128'hd4bf5d30e0b452aeb84111f11e2798e5)
            $fatal(1, "FIPS SubBytes/ShiftRows mismatch");
        state_in = shifted;
        #1;
        if (mixed !== 128'h046681e5e0cb199a48f8d37a2806264c)
            $fatal(1, "FIPS MixColumns mismatch");

        for (n = 0; n < 128 + 256; n = n + 1) begin
            if (n < 128) state_in = 128'b1 << n;
            else begin
                random_state = {random_state[126:0], random_state[127] ^ random_state[125] ^ random_state[100] ^ random_state[98]};
                state_in = random_state;
            end
            for (r = 0; r < 4; r = r + 1)
                for (c = 0; c < 4; c = c + 1)
                    expected_shift[127-8*(4*c+r) -: 8] = algebra_sbox(state_in[127-8*(4*((c+r)%4)+r) -: 8]);
            #1;
            if (mixed !== matrix_mix(state_in) || shifted !== expected_shift)
                $fatal(1, "Round transforms mismatch at sample %0d", n);
        end
        $display("PASS aes_components: 256 algebraic S-box checks; 10 FIPS round keys; published intermediate states; 384 transform inputs");
        $finish;
    end
    initial begin
        #100000;
        $fatal(1, "AES components watchdog timeout");
    end
endmodule

`default_nettype wire
