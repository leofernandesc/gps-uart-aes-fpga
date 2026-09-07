`timescale 1ns/1ps
`default_nettype none

module uart_top_tb #(
    parameter integer CLK_FREQ = 307200,
    parameter integer NUM_BYTES = 64
);
    localparam integer BAUD_RATE = 9600;
    localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;
    localparam realtime SERIAL_BIT_NS = (1.0 * CLK_FREQ / BAUD_RATE) * 20.0;
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst = 1;
    reg rx = 1;
    reg tx_start = 0;
    reg [7:0] tx_data = 0;
    wire tx, tx_busy, tx_done, tx_ready;
    wire [7:0] rx_data;
    wire rx_done, rx_framing_error;
    uart_top #(.CLK_FREQ(CLK_FREQ), .BAUD_RATE(BAUD_RATE)) dut (.*);

    integer rx_count = 0, tx_count = 0, decoded_count = 0;
    reg previous_rx_done = 0, previous_tx_done = 0;
    always @(posedge clk) begin
        #1;
        if (!rst) begin
            if (rx_framing_error !== 0) $fatal(1, "Top-level RX framing error");
            if ((rx_done && previous_rx_done) || (tx_done && previous_tx_done))
                $fatal(1, "Top-level done pulse exceeded one clock");
            if (tx_ready && tx_busy) $fatal(1, "TX ready while busy");
            if (rx_done) begin
                if (rx_data !== 8'(255 - rx_count))
                    $fatal(1, "Full-duplex RX byte %0d mismatch: %02x", rx_count, rx_data);
                rx_count = rx_count + 1;
            end
            if (tx_done) tx_count = tx_count + 1;
            previous_rx_done = rx_done;
            previous_tx_done = tx_done;
        end
    end

    initial begin
        #37;
        if (tx_ready !== 0 || tx !== 1) $fatal(1, "Top not reset");
        rst = 0;
        #1;
        if (tx_ready !== 0) $fatal(1, "Reset released asynchronously");
        @(posedge clk);
        #1;
        if (tx_ready !== 0) $fatal(1, "Reset released after only one edge");
        @(posedge clk);
        #1;
        if (tx_ready !== 1) $fatal(1, "Reset failed to release after two edges");
        #(2 * SERIAL_BIT_NS);

        fork
            begin : external_serial_source
                integer n, b;
                reg [7:0] data;
                #7;
                for (n = 0; n < NUM_BYTES; n = n + 1) begin
                    data = 8'(255 - n);
                    rx = 0;
                    #(SERIAL_BIT_NS);
                    for (b = 0; b < 8; b = b + 1) begin
                        rx = data[b];
                        #(SERIAL_BIT_NS);
                    end
                    rx = 1;
                    #(SERIAL_BIT_NS);
                end
            end
            begin : tx_requests
                integer n;
                for (n = 0; n < NUM_BYTES; n = n + 1) begin
                    @(negedge clk);
                    while (!tx_ready) @(negedge clk);
                    tx_data = 8'(n) ^ 8'ha5;
                    tx_start = 1;
                    @(negedge clk);
                    tx_start = 0;
                end
            end
            begin : external_serial_decoder
                integer n, b;
                reg [7:0] observed;
                for (n = 0; n < NUM_BYTES; n = n + 1) begin
                    @(negedge tx);
                    #(SERIAL_BIT_NS / 2.0);
                    if (tx !== 0) $fatal(1, "External decoder: start too short");
                    for (b = 0; b < 8; b = b + 1) begin
                        #(SERIAL_BIT_NS);
                        observed[b] = tx;
                    end
                    #(SERIAL_BIT_NS);
                    if (tx !== 1) $fatal(1, "External decoder: bad stop");
                    if (observed !== (8'(n) ^ 8'ha5))
                        $fatal(1, "External decoder TX byte %0d mismatch", n);
                    decoded_count = decoded_count + 1;
                end
            end
        join
        #(2 * SERIAL_BIT_NS);
        if (rx_count != NUM_BYTES || tx_count != NUM_BYTES || decoded_count != NUM_BYTES)
            $fatal(1, "Full-duplex counts mismatch rx=%0d tx=%0d decoded=%0d", rx_count, tx_count, decoded_count);

        // A second asynchronous reset must suppress readiness immediately.
        #3;
        rst = 1;
        #1;
        if (tx_ready !== 0 || tx !== 1 || rx_done !== 0 || tx_done !== 0)
            $fatal(1, "Top reset reassertion failed");
        $display("PASS uart_top CLK_FREQ=%0d CPB=%0d: %0d full-duplex bytes each way; external decoder; reset release", CLK_FREQ, CLKS_PER_BIT, NUM_BYTES);
        $finish;
    end

    initial begin
        #(SERIAL_BIT_NS * (NUM_BYTES + 10) * 12);
        $fatal(1, "Top-level watchdog timeout");
    end
endmodule

`default_nettype wire
