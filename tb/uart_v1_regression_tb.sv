`timescale 1ns/1ps
`default_nettype none

// A passing test here means the known v1 defect was reproduced AND v2 fixed it.
module uart_v1_regression_tb;
    localparam integer CLKS_PER_BIT = 32;
    localparam time BIT_NS = 640;
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst = 1, tx_start = 0;
    wire baud_tick, tx_old, tx_new;
    wire old_busy, old_done, new_busy, new_done;
    realtime start_ns, old_width, new_width;

    baud_gen #(.CLK_FREQ(307200), .BAUD_RATE(9600)) baud_v1 (
        .clk(clk), .rst(rst), .baud_tick(baud_tick)
    );
    uart_tx_v1 old_tx (
        .clk(clk), .rst(rst), .baud_tick(baud_tick), .tx_start(tx_start),
        .tx_data(8'hff), .tx(tx_old), .tx_busy(old_busy), .tx_done(old_done)
    );
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) new_tx (
        .clk(clk), .rst(rst), .tx_start(tx_start), .tx_data(8'hff),
        .tx(tx_new), .tx_busy(new_busy), .tx_done(new_done)
    );

    initial begin
        #43;
        @(negedge clk);
        rst = 0;
        repeat (7) @(negedge clk);
        tx_start = 1;
        @(posedge clk);
        start_ns = $realtime;
        #1;
        if (tx_old !== 0 || tx_new !== 0) $fatal(1, "Regression setup did not start TX");
        fork
            begin
                @(negedge clk);
                tx_start = 0;
            end
            begin
                @(posedge tx_old);
                old_width = $realtime - start_ns;
            end
            begin
                @(posedge tx_new);
                new_width = $realtime - start_ns;
            end
        join
        if (!(old_width > 0 && old_width < BIT_NS))
            $fatal(1, "Expected v1 truncated start was not reproduced");
        if (new_width != BIT_NS)
            $fatal(1, "v2 start width %0.1f ns, expected %0t", new_width, BIT_NS);
        $display("PASS v1 regression: old start=%0.1f ns; revised start=%0.1f ns; required=%0.1f ns", old_width, new_width, 1.0 * BIT_NS);
        $finish;
    end

    initial begin
        #(BIT_NS * 20);
        $fatal(1, "v1 regression watchdog timeout");
    end
endmodule

`default_nettype wire
