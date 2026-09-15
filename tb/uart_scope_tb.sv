`timescale 1ns/1ps
`default_nettype none

module uart_scope_tb #(
    parameter integer CLK_FREQ = 307200,
    parameter integer PERIOD_CYCLES = CLK_FREQ / 10
);
    localparam integer CPB = CLK_FREQ / 9600;
    localparam time BIT_NS = CPB * 20;
    localparam time PERIOD_NS = PERIOD_CYCLES * 20;
    reg clk = 0;
    always #10 clk = ~clk;
    reg arst = 1, loopback = 0, external_rx = 1;
    wire tx, rx_seen, error_sticky;
    wire rx = loopback ? tx : external_rx;
    wire [7:0] last_rx_data;
    uart_scope #(.CLK_FREQ(CLK_FREQ), .PERIOD_CYCLES(PERIOD_CYCLES)) dut (
        .clk(clk), .arst(arst), .rx(rx), .tx(tx), .last_rx_data(last_rx_data),
        .rx_seen(rx_seen), .error_sticky(error_sticky)
    );

    // Independent decoder reads the pin only. Verify every bit's full width.
    task automatic check_tx;
        integer bit_number;
        reg [9:0] expected_frame;
        begin
            expected_frame = {1'b1, 8'h55, 1'b0};
            @(negedge tx);
            for (bit_number = 0; bit_number < 10; bit_number = bit_number + 1) begin
                #1;
                if (tx !== expected_frame[bit_number]) $fatal(1, "Scope TX bit start");
                #(BIT_NS - 2);
                if (tx !== expected_frame[bit_number]) $fatal(1, "Scope TX bit too short");
                #1;
            end
            #1;
            if (tx !== 1) $fatal(1, "Scope TX did not idle high");
        end
    endtask

    task automatic send_frame(input reg [7:0] data, input reg stop_bit);
        integer b;
        begin
            #7;
            external_rx = 0;
            #(BIT_NS);
            for (b = 0; b < 8; b = b + 1) begin
                external_rx = data[b];
                #(BIT_NS);
            end
            external_rx = stop_bit;
            #(BIT_NS);
            external_rx = 1;
            #(2 * BIT_NS);
        end
    endtask

    time first_start;
    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/uart_scope.vcd");
            $dumpvars(0, arst, rx, tx, loopback, last_rx_data, rx_seen, error_sticky);
        end
        #37;
        arst = 0;
        fork
            begin
                @(negedge tx);
                // Reset releases at 70 ns; stimulus is accepted PERIOD_CYCLES later.
                if ($time != 70 + PERIOD_NS) $fatal(1, "First stimulus period mismatch");
                first_start = $time;
                #(11 * BIT_NS);
                @(negedge tx);
                if ($time - first_start != PERIOD_NS) $fatal(1, "Stimulus repetition mismatch");
            end
            begin check_tx(); check_tx(); end
        join
        if (rx_seen !== 0 || error_sticky !== 0) $fatal(1, "Disconnected RX accepted data");
        loopback = 1;
        check_tx();
        #100;
        if (rx_seen !== 1 || error_sticky !== 0 || last_rx_data !== 8'h55)
            $fatal(1, "External loopback failed");
        loopback = 0;
        // An independent source can test RX without the transmitter's timing.
        send_frame(8'h55, 1);
        if (error_sticky !== 0) $fatal(1, "Independent valid RX rejected");
        send_frame(8'ha6, 1);
        if (error_sticky !== 1 || last_rx_data !== 8'ha6)
            $fatal(1, "Mismatch not displayed");
        send_frame(8'h55, 1);
        if (error_sticky !== 1) $fatal(1, "Error flag was not persistent");
        #3; arst = 1; #71; arst = 0;
        #(2 * BIT_NS);
        if (rx_seen !== 0 || error_sticky !== 0 || last_rx_data !== 0)
            $fatal(1, "Reset did not clear diagnostics");
        send_frame(8'h55, 0);
        if (error_sticky !== 1 || rx_seen !== 0) $fatal(1, "Bad stop accepted");
        @(negedge tx);
        #(2 * BIT_NS + 3);
        arst = 1; #1;
        if (tx !== 1 || rx_seen !== 0 || error_sticky !== 0)
            $fatal(1, "Reset during TX failed");
        #71; arst = 0;
        loopback = 1;
        check_tx();
        #100;
        if (rx_seen !== 1 || error_sticky !== 0 || last_rx_data !== 8'h55)
            $fatal(1, "Recovery failed");
        $display("PASS uart_scope CLK_FREQ=%0d PERIOD_CYCLES=%0d: TX timing/period, disconnected RX, physical-loopback model, independent RX, mismatch/framing, reset", CLK_FREQ, PERIOD_CYCLES);
        $finish;
    end
    initial begin
        #(20 * PERIOD_NS);
        $fatal(1, "Scope watchdog");
    end
endmodule

`default_nettype wire
