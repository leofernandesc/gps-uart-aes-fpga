`timescale 1ns/1ps
`default_nettype none

// Compile-time provisioning test for the DE10-Lite wrapper.  The test uses a
// context different from the wrapper default and observes only the UART TX
// wire, as an external receiver would do.
module de10_lite_uart_ctr_top_tb;
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

    reg key0_n = 1'b0;
    reg uart_rx = 1'b1;
    wire uart_tx;
    wire [9:0] leds;

    de10_lite_uart_ctr_top #(
        .ENABLE_AES      (1),
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
        repeat (10) @(posedge clk);
        key0_n = 1'b1;

        timeout = 0;
        while (!leds[5] && timeout < 1000) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (!leds[5]) $fatal(1, "Wrapper did not complete custom context setup");

        // uart_rx requires one complete idle bit after datapath reset before
        // it arms the start-bit detector.
        repeat (5208 + 50) @(posedge clk);
        send_byte(PLAINTEXT);
    end

    initial begin : decoder
        integer bit_index;
        reg [7:0] decoded;
        @(negedge uart_tx);
        #(BIT_NS / 2);
        if (uart_tx !== 1'b0) $fatal(1, "Invalid TX start bit");
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
            #(BIT_NS);
            decoded[bit_index] = uart_tx;
        end
        #(BIT_NS);
        if (uart_tx !== 1'b1) $fatal(1, "Invalid TX stop bit");
        if (decoded !== EXPECTED_CIPHERTEXT)
            $fatal(1, "Custom context mismatch: got=%02x expected=%02x",
                   decoded, EXPECTED_CIPHERTEXT);
        $display("PASS DE10-Lite wrapper custom context: plaintext=%02x ciphertext=%02x",
                 PLAINTEXT, decoded);
        $finish;
    end

    initial begin
        #5000000;
        $fatal(1, "Wrapper custom-context watchdog");
    end
endmodule

`default_nettype wire
