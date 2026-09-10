`timescale 1ns/1ps
`default_nettype none

module aes128_ctr_mask_tb;
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst = 1, abort_req = 0, cfg_valid = 0, mask_ready = 0;
    reg [127:0] cfg_key = 0;
    reg [95:0] cfg_nonce = 0;
    reg [31:0] cfg_counter = 0;
    wire cfg_ready, cfg_done, active, exhausted, mask_valid, mask_last;
    wire [127:0] mask_data;
    aes128_ctr_mask dut (.*);

    reg stalled = 0;
    reg [127:0] held_mask;
    reg held_last;
    integer blocks_seen = 0, stalls_seen = 0;
    always @(posedge clk) begin
        if (rst || abort_req) stalled = 0;
        else begin
            if ((^{cfg_ready,cfg_done,active,exhausted,mask_valid,mask_last}) === 1'bx)
                $fatal(1, "CTR mask unknown control");
            if (stalled && (!mask_valid || mask_data !== held_mask || mask_last !== held_last))
                $fatal(1, "CTR mask changed under backpressure");
            if (mask_valid && !active) $fatal(1, "Mask without configuration");
            if (active && cfg_ready) $fatal(1, "Active configuration may not be overwritten");
            if (exhausted && mask_valid) $fatal(1, "Exhausted before final mask accepted");
            stalled = mask_valid && !mask_ready;
            held_mask = mask_data;
            held_last = mask_last;
            if (stalled) stalls_seen = stalls_seen + 1;
        end
    end

    integer fd, count, n, j, scan, block_count, last_expected, wait_cycles;
    reg [127:0] key, expected;
    reg [95:0] nonce;
    reg [31:0] initial_counter;
    initial begin
        #1;
        rst = 0;
        #1;
        rst = 1;
        repeat (3) @(negedge clk);
        rst = 0;
        mask_ready = 1;
        repeat (6) begin
            @(posedge clk);
            #1;
            if (mask_valid || exhausted || active) $fatal(1, "Mask before configuration");
        end
        fd = $fopen("build/ctr/mask-vectors.txt", "r");
        if (!fd || $fscanf(fd, "%d\n", count) != 1 || count < 1)
            $fatal(1, "Missing CTR mask vectors");
        for (n = 0; n < count; n = n + 1) begin
            scan = $fscanf(fd, "%h %h %h %d\n", key, nonce, initial_counter, block_count);
            if (scan != 4) $fatal(1, "Malformed mask header");
            @(negedge clk);
            abort_req = 1;
            cfg_valid = 1; // Abort must win over configuration.
            #1;
            if (cfg_ready || mask_valid) $fatal(1, "Abort handshake suppression failed");
            @(negedge clk);
            abort_req = 0;
            cfg_valid = 0;
            while (!cfg_ready) @(negedge clk);
            cfg_key = key;
            cfg_nonce = nonce;
            cfg_counter = initial_counter;
            cfg_valid = 1;
            mask_ready = 0;
            @(posedge clk);
            #1;
            if (!active || cfg_ready) $fatal(1, "Mask configuration failed");
            @(negedge clk);
            // Held-high requests and changed config pins may not rekey an active context.
            cfg_key = ~key;
            cfg_nonce = ~nonce;
            cfg_counter = ~initial_counter;
            for (j = 0; j < block_count; j = j + 1) begin
                scan = $fscanf(fd, "%h %d\n", expected, last_expected);
                if (scan != 2) $fatal(1, "Malformed mask data");
                wait_cycles = 0;
                begin : await_mask
                    forever begin
                        @(negedge clk);
                        mask_ready = (wait_cycles > 70 && wait_cycles % 5 != 0);
                        @(posedge clk);
                        if (mask_valid && mask_ready) begin
                            if (mask_data !== expected || mask_last !== 1'(last_expected))
                                $fatal(1, "Mask mismatch session=%0d block=%0d", n, j);
                            blocks_seen = blocks_seen + 1;
                            disable await_mask;
                        end
                        wait_cycles = wait_cycles + 1;
                        if (wait_cycles > 200) $fatal(1, "CTR mask timeout");
                    end
                end
                @(negedge clk);
                mask_ready = 0;
            end
            if (last_expected) begin
                mask_ready = 1;
                repeat (80) begin
                    @(posedge clk);
                    #1;
                    if (!exhausted || mask_valid || cfg_ready)
                        $fatal(1, "Counter wrapped or last mask repeated");
                end
            end
        end
        $fclose(fd);
        if (stalls_seen < 100) $fatal(1, "Insufficient stall coverage");
        $display("PASS aes128_ctr_mask: %0d sessions; %0d masks; %0d stalled cycles; held config; abort; no wrap",
                 count, blocks_seen, stalls_seen);
        $finish;
    end
    initial begin
        #20000000;
        $fatal(1, "CTR mask watchdog");
    end
endmodule

`default_nettype wire
