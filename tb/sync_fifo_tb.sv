`timescale 1ns/1ps
`default_nettype none

module sync_fifo_tb #(
    parameter integer DEPTH = 8
);
    localparam integer LEVEL_WIDTH = $clog2(DEPTH + 1);
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst = 1, wr_en = 0, rd_en = 0;
    reg [7:0] wr_data = 0;
    wire [7:0] rd_data;
    wire rd_valid, empty, full, overflow;
    wire [LEVEL_WIDTH-1:0] level, high_water;
    sync_fifo #(.DEPTH(DEPTH)) dut (.*);

    // Linear software queue, independent of DUT pointers and memory addressing.
    reg [7:0] queue [0:65535];
    integer head = 0, tail = 0, count = 0, peak = 0;
    integer steps = 0, reads = 0, drops = 0, n;
    reg [31:0] random_state = 32'h6d28a951;

    task automatic cycle(input reg write_request, input reg read_request, input reg [7:0] data);
        reg do_read, do_write, dropped;
        reg [7:0] expected_data;
        begin
            @(negedge clk);
            wr_en = write_request;
            rd_en = read_request;
            wr_data = data;
            do_read = read_request && count != 0;
            do_write = write_request && (count != DEPTH || do_read);
            dropped = write_request && !do_write;
            if (do_read) begin
                expected_data = queue[head];
                head = head + 1;
                count = count - 1;
                reads = reads + 1;
            end
            if (do_write) begin
                queue[tail] = data;
                tail = tail + 1;
                count = count + 1;
            end
            if (count > peak) peak = count;
            if (dropped) drops = drops + 1;
            @(posedge clk);
            #1;
            if (rd_valid !== do_read || overflow !== dropped)
                $fatal(1, "FIFO response mismatch at step %0d", steps);
            if (do_read && rd_data !== expected_data)
                $fatal(1, "FIFO order/data mismatch: %02x != %02x", rd_data, expected_data);
            if (level !== LEVEL_WIDTH'(count) || high_water !== LEVEL_WIDTH'(peak))
                $fatal(1, "FIFO occupancy mismatch level=%0d expected=%0d peak=%0d expected=%0d", level, count, high_water, peak);
            if (empty !== (count == 0) || full !== (count == DEPTH))
                $fatal(1, "FIFO flags mismatch");
            steps = steps + 1;
        end
    endtask

    task automatic reset_fifo;
        begin
            @(negedge clk);
            rst = 1;
            wr_en = 0;
            rd_en = 0;
            head = 0;
            tail = 0;
            count = 0;
            peak = 0;
            #1;
            if (level !== 0 || high_water !== 0 || rd_valid !== 0 || overflow !== 0)
                $fatal(1, "FIFO reset did not invalidate data/status");
            repeat (2) @(negedge clk);
            rst = 0;
        end
    endtask

    initial begin
        #31;
        reset_fifo();
        cycle(0, 1, 0); // Empty read is ignored.
        cycle(1, 1, 8'ha5); // Empty read/write: store only, no implicit bypass.
        cycle(0, 1, 0);
        for (n = 0; n < DEPTH; n = n + 1) cycle(1, 0, 8'(n));
        cycle(1, 0, 8'hde); // Full: reject newest byte.
        for (n = 0; n < 2 * DEPTH; n = n + 1)
            cycle(1, 1, 8'(n) ^ 8'h5a); // Full simultaneous replacement, old data.
        while (count != 0) cycle(0, 1, 0);
        cycle(0, 1, 0);

        for (n = 0; n < 20000; n = n + 1) begin
            random_state = {random_state[30:0], random_state[31] ^ random_state[21] ^ random_state[1] ^ random_state[0]};
            cycle(random_state[0], random_state[7], random_state[15:8]);
        end
        while (count != 0) cycle(0, 1, 0);
        for (n = 0; n < DEPTH; n = n + 1) cycle(1, 0, 8'hcc);
        reset_fifo(); // Non-empty reset must not expose old RAM contents.
        cycle(0, 1, 0);
        cycle(1, 0, 8'h37);
        cycle(0, 1, 0);
        cycle(0, 0, 0);
        if (drops == 0) $fatal(1, "Overflow coverage absent");
        $display("PASS sync_fifo DEPTH=%0d: %0d cycles, %0d ordered reads, %0d rejected writes; full collision; wrap; empty; reset", DEPTH, steps, reads, drops);
        $finish;
    end

    initial begin
        #10000000;
        $fatal(1, "FIFO watchdog timeout");
    end
endmodule

`default_nettype wire
