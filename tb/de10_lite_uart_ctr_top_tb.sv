`timescale 1ns/1ps
`default_nettype none

// Compile-time provisioning test for the DE10-Lite wrapper.  The test uses a
// context different from the wrapper default and observes only the UART TX
// wire, as an external receiver would do.
module de10_lite_uart_ctr_top_tb;
    parameter integer ENABLE_AES = 1;
    localparam [127:0] CONTEXT_KEY =
        128'heea81777c2f0b6bec6a98d56a467f786;
    localparam [95:0] CONTEXT_NONCE =
        96'he31fa2f0ae6bde367f10d234;
    localparam [31:0] CONTEXT_COUNTER = 32'h000000ff;
    localparam [7:0] PLAINTEXT = 8'h55;
    localparam [7:0] EXPECTED_CIPHERTEXT = 8'he2;
    localparam integer BIT_NS = 5208 * 20;

    reg clk = 1'b0;
    always #10 clk = !clk;

    // Exercise power-up without a manual reset as well as KEY0.
    reg key0_n = 1'b1;
    reg uart_rx = 1'b1;
    wire uart_tx;
    wire [9:0] leds;
    reg first_byte_done = 1'b0;
    integer tx_starts = 0;

    de10_lite_uart_ctr_top #(
        .ENABLE_AES      (ENABLE_AES),
        .CONTEXT_KEY     (CONTEXT_KEY),
        .CONTEXT_NONCE   (CONTEXT_NONCE),
        .CONTEXT_COUNTER (CONTEXT_COUNTER)
    ) dut (
        .MAX10_CLK1_50 (clk),
        .KEY0_N        (key0_n),
        .UART_RX       (uart_rx),
        .UART_TX       (uart_tx),
        .LEDR          (leds)
    );

    task automatic send_byte(input reg [7:0] value);
        integer bit_index;
        begin
            // Deliberately do not align the source to the FPGA clock.
            #7 uart_rx = 1'b0;
            #(BIT_NS);
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                uart_rx = value[bit_index];
                #(BIT_NS);
            end
            uart_rx = 1'b1;
            #(BIT_NS);
            uart_rx = 1'b1;
            #(BIT_NS / 2);
        end
    endtask

    initial begin : stimulus
        integer timeout;
        timeout = 0;
        while (!leds[5] && timeout < 1000) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (!leds[5]) $fatal(1, "Wrapper did not complete custom context setup");

        // No bytes consumed: resetting before acquisition must still work.
        @(negedge clk) key0_n = 1'b0;
        repeat (10) @(negedge clk);
        key0_n = 1'b1;
        repeat (100) @(negedge clk);
        if (!leds[5] || !leds[1] || leds[9])
            $fatal(1, "Reset before reception did not rearm safely");

        // uart_rx requires one complete idle bit after datapath reset before
        // it arms the start-bit detector.
        repeat (5208 + 50) @(posedge clk);
        send_byte(PLAINTEXT);
        wait (first_byte_done);
        repeat (5208) @(negedge clk);
        // A second plaintext after reset must not reuse the first CTR mask.
        key0_n = 1'b0;
        repeat (10) @(negedge clk);
        key0_n = 1'b1;
        repeat (5208 + 100) @(negedge clk);
        if (leds[1] || leds[5] || !leds[9])
            $fatal(1, "Used context did not lock after reset");
        send_byte(8'haa);
        repeat (12 * 5208) @(negedge clk);
        if (tx_starts != 1 || uart_tx !== 1'b1 || leds[1])
            $fatal(1, "Reset reused a consumed context");
        $display("PASS DE10-Lite wrapper aes=%0d: power-up, custom context, pre-data reset, post-data reset lockout", ENABLE_AES);
        $finish;
    end

    always @(negedge uart_tx) begin
        if (first_byte_done) $fatal(1, "TX transition after used-context reset");
    end

    initial begin : decoder
        integer bit_index;
        reg [7:0] decoded;
        @(negedge uart_tx);
        tx_starts = tx_starts + 1;
        #(BIT_NS / 2);
        if (uart_tx !== 1'b0) $fatal(1, "Invalid TX start bit");
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
            #(BIT_NS);
            decoded[bit_index] = uart_tx;
        end
        #(BIT_NS);
        if (uart_tx !== 1'b1) $fatal(1, "Invalid TX stop bit");
        if (decoded !== (ENABLE_AES ? EXPECTED_CIPHERTEXT : PLAINTEXT))
            $fatal(1, "Custom context mismatch: got=%02x expected=%02x",
                   decoded, ENABLE_AES ? EXPECTED_CIPHERTEXT : PLAINTEXT);
        first_byte_done = 1'b1;
    end

    initial begin
        #10000000;
        $fatal(1, "Wrapper custom-context watchdog");
    end
endmodule

`default_nettype wire
