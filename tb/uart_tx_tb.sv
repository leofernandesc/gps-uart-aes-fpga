`timescale 1ns/1ps
`default_nettype none

module uart_tx_tb #(
    parameter integer CLKS_PER_BIT = 32
);
    localparam time CLOCK_NS = 20;
    localparam time BIT_NS = CLOCK_NS * CLKS_PER_BIT;
    reg clk = 0;
    always #(CLOCK_NS / 2) clk = ~clk;
    reg rst = 1;
    reg tx_start = 0;
    reg [7:0] tx_data = 0;
    wire tx, tx_busy, tx_done;
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) dut (.*);

    integer value, completed = 0, before_completed;
    reg previous_done = 0;
    always @(posedge clk) begin
        #1;
        if (rst) begin
            previous_done = 0;
        end else begin
            if (tx_done && previous_done) $fatal(1, "tx_done exceeded one cycle");
            if (tx_done && tx_busy) $fatal(1, "tx_busy still set at completion");
            if (tx_done) completed = completed + 1;
            previous_done = tx_done;
        end
    end

    task automatic send_and_check(input reg [7:0] data);
        integer cycle_number;
        reg [9:0] expected_frame;
        begin
            expected_frame = {1'b1, data, 1'b0};
            @(negedge clk);
            if (tx_busy !== 0) $fatal(1, "TX not ready for request");
            tx_data = data;
            tx_start = 1;
            @(posedge clk);
            #1;
            fork
                begin
                    @(negedge clk);
                    tx_start = 0;
                    tx_data = ~data;
                    // A pulsed request while busy must not overwrite/queue data.
                    repeat (2 * CLKS_PER_BIT) @(negedge clk);
                    tx_start = 1;
                    @(negedge clk);
                    tx_start = 0;
                end
                begin
                    // Check every clock, including both sides of each boundary.
                    for (cycle_number = 0; cycle_number < 10 * CLKS_PER_BIT; cycle_number = cycle_number + 1) begin
                        if (cycle_number != 0) begin
                            @(posedge clk);
                            #1;
                        end
                        if (tx !== expected_frame[cycle_number / CLKS_PER_BIT] || tx_busy !== 1 || tx_done !== 0)
                            $fatal(1, "TX byte %02x cycle %0d: tx=%b busy=%b done=%b", data, cycle_number, tx, tx_busy, tx_done);
                    end
                    @(posedge clk);
                    #1;
                    if (tx !== 1 || tx_busy !== 0 || tx_done !== 1)
                        $fatal(1, "TX completion was not exactly 10 full bits");
                end
            join
            // Return now: the next call can request at the very first ready edge.
        end
    endtask

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/uart_tx.vcd");
            $dumpvars(0, uart_tx_tb);
        end
        #53;
        if (tx !== 1 || tx_busy !== 0 || tx_done !== 0)
            $fatal(1, "TX reset outputs invalid");
        rst = 0;
        for (value = 0; value < 256; value = value + 1)
            send_and_check(8'(value));
        #(12 * BIT_NS);
        if (completed != 256) $fatal(1, "Unexpected queued or missing TX frame");

        // Asynchronous reset must immediately release the line and abort the byte.
        @(negedge clk);
        tx_data = 8'h00;
        tx_start = 1;
        @(negedge clk);
        tx_start = 0;
        #(3 * BIT_NS + 3);
        before_completed = completed;
        rst = 1;
        #1;
        if (tx !== 1 || tx_busy !== 0 || tx_done !== 0)
            $fatal(1, "TX did not abort on asynchronous reset");
        #57;
        rst = 0;
        #(12 * BIT_NS);
        if (completed != before_completed) $fatal(1, "Aborted TX asserted done");
        send_and_check(8'h55);
        #(2 * BIT_NS);
        if (completed != 257) $fatal(1, "TX failed after reset");
        $display("PASS uart_tx CPB=%0d: 257 frames; every cycle/bit width; busy rejection; earliest ready; reset", CLKS_PER_BIT);
        $finish;
    end

    initial begin
        #(BIT_NS * 5000);
        $fatal(1, "TX watchdog timeout");
    end
endmodule

`default_nettype wire
