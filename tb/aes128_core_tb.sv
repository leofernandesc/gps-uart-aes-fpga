`timescale 1ns/1ps
`default_nettype none

module aes128_core_tb;
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst = 1, key_load = 0, start = 0;
    reg [127:0] key_in = 0, block_in = 0;
    wire key_ready, key_valid, key_done, block_ready, busy, done;
    wire [127:0] ciphertext;
    aes128_core dut (.*);

    localparam [127:0] TEST_KEY = 128'h000102030405060708090a0b0c0d0e0f;
    localparam [127:0] TEST_BLOCK = 128'h00112233445566778899aabbccddeeff;
    localparam [127:0] TEST_CIPHER = 128'h69c4e0d86a7b0430d8cdb78070b4c55a;
    integer cycles = 0, completions = 0, key_completions = 0;
    integer last_accept = -1, min_interval = 1000000;
    reg previous_done = 0, previous_key_done = 0;
    reg [127:0] previous_cipher = 0;
    reg accepted_key;
    always @(posedge clk) begin
        cycles = cycles + 1;
        accepted_key = key_load && key_ready;
        #2;
        if (rst) begin
            previous_done = 0;
            previous_key_done = 0;
            previous_cipher = 0;
        end else begin
            // Reduction-XOR detects any X/Z and works across our simulators.
            if ((^{key_ready,key_valid,key_done,block_ready,busy,done}) === 1'bx)
                $fatal(1, "AES unknown control output: %b%b%b%b%b%b",
                       key_ready,key_valid,key_done,block_ready,busy,done);
            if ((done && previous_done) || (key_done && previous_key_done) || (done && key_done))
                $fatal(1, "AES completion pulse contract failed");
            if ((done || key_done) && busy) $fatal(1, "Completion while still busy");
            if (block_ready && (!key_valid || busy || key_load)) $fatal(1, "Invalid block_ready");
            if (!done && !accepted_key && ciphertext !== previous_cipher)
                $fatal(1, "Ciphertext changed without completion/rekey");
            if (done) completions = completions + 1;
            if (key_done) key_completions = key_completions + 1;
            previous_done = done;
            previous_key_done = key_done;
            previous_cipher = ciphertext;
        end
    end

    task automatic reset_core;
        integer i;
        begin
            @(negedge clk);
            #3;
            rst = 1;
            start = 0;
            key_load = 0;
            #1;
            if (busy !== 0 || done !== 0 || key_done !== 0 || key_valid !== 0 ||
                key_ready !== 0 || block_ready !== 0 || ciphertext !== 0)
                $fatal(1, "AES asynchronous reset failed");
            for (i = 0; i < 11; i = i + 1)
                if (dut.round_keys[i] !== 0) $fatal(1, "Key storage not cleared on reset");
            // Reset storage is checked directly; the encryption oracle uses only ports.
            repeat (2) @(negedge clk);
            rst = 0;
            #1;
            if (!key_ready || block_ready) $fatal(1, "AES ready before provisioning");
        end
    endtask

    task automatic load_key(input reg [127:0] key, input reg collision);
        integer step, accepted;
        begin
            @(negedge clk);
            if (!key_ready) $fatal(1, "AES not ready for key");
            key_in = key;
            key_load = 1;
            start = collision;
            #1;
            if (block_ready) $fatal(1, "Key load did not take priority");
            @(posedge clk);
            #1;
            accepted = cycles;
            if (!busy || key_valid || key_done || done || ciphertext !== 0)
                $fatal(1, "AES key acceptance failed");
            @(negedge clk);
            key_load = 0;
            start = 0;
            key_in = ~key;
            for (step = 1; step <= 10; step = step + 1) begin
                @(posedge clk);
                #1;
                if (step < 10) begin
                    if (!busy || key_ready || key_valid || key_done || block_ready || done)
                        $fatal(1, "AES premature key completion");
                    @(negedge clk);
                    key_load = (step == 2);
                    start = (step == 3);
                end else if (!key_valid || !key_done || busy || done || cycles-accepted != 10)
                    $fatal(1, "AES key latency must be 10 cycles");
            end
        end
    endtask

    task automatic encrypt_block(input reg [127:0] plaintext, input reg [127:0] expected);
        integer step, accepted, interval;
        begin
            @(negedge clk);
            if (!block_ready) $fatal(1, "AES not ready for block");
            block_in = plaintext;
            start = 1;
            @(posedge clk);
            #1;
            accepted = cycles;
            if (last_accept >= 0) begin
                interval = cycles-last_accept;
                if (interval < min_interval) min_interval = interval;
                if (interval < 21) $fatal(1, "AES accepted too early");
            end
            last_accept = cycles;
            if (!busy || block_ready || done) $fatal(1, "AES block acceptance failed");
            @(negedge clk);
            start = 0;
            block_in = ~plaintext;
            for (step = 1; step <= 20; step = step + 1) begin
                @(posedge clk);
                #1;
                if (step < 20) begin
                    if (!busy || key_ready || block_ready || done || !key_valid)
                        $fatal(1, "AES premature block completion");
                    @(negedge clk);
                    // Neither request may queue or interrupt the active block.
                    key_load = (step == 2);
                    start = (step == 5);
                    key_in = ~TEST_KEY;
                end else begin
                    if (!done || busy || !block_ready || key_done || cycles-accepted != 20)
                        $fatal(1, "AES block latency must be 20 cycles");
                    if (ciphertext !== expected)
                        $fatal(1, "AES ciphertext %032x != %032x", ciphertext, expected);
                end
            end
        end
    endtask

    integer vectors_file, vector_count, scan, n, abort_cycle, step, before_count;
    reg [127:0] key, plaintext, expected, loaded_key;
    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/aes/core.vcd");
            $dumpvars(0, aes128_core_tb);
        end
        #33;
        reset_core();
        start = 1;
        repeat (4) @(negedge clk);
        if (busy || done || block_ready) $fatal(1, "Block accepted without key");
        start = 0;
        load_key(TEST_KEY, 1);
        encrypt_block(TEST_BLOCK, TEST_CIPHER);

        vectors_file = $fopen("build/aes/vectors.txt", "r");
        if (!vectors_file) $fatal(1, "Missing independent AES vectors");
        scan = $fscanf(vectors_file, "%d\n", vector_count);
        if (scan != 1 || vector_count != 866) $fatal(1, "Unexpected AES vector count");
        loaded_key = TEST_KEY;
        for (n = 0; n < vector_count; n = n + 1) begin
            scan = $fscanf(vectors_file, "%h %h %h\n", key, plaintext, expected);
            if (scan != 3) $fatal(1, "Malformed AES vector %0d", n);
            if (key !== loaded_key) begin
                load_key(key, 0);
                loaded_key = key;
            end
            encrypt_block(plaintext, expected);
        end
        $fclose(vectors_file);
        repeat (25) @(negedge clk);
        if (busy || done) $fatal(1, "Busy requests were queued");
        if (min_interval != 21) $fatal(1, "Earliest initiation interval not covered");

        // Reset every intermediate key-expansion cycle and every cipher stage.
        for (abort_cycle = 1; abort_cycle < 10; abort_cycle = abort_cycle + 1) begin
            reset_core();
            @(negedge clk);
            key_load = 1;
            key_in = TEST_KEY;
            @(negedge clk);
            key_load = 0;
            repeat (abort_cycle-1) @(negedge clk);
            reset_core();
            repeat (24) @(negedge clk);
            if (key_valid || key_done || done || busy) $fatal(1, "Aborted expansion completed");
        end
        for (abort_cycle = 1; abort_cycle < 20; abort_cycle = abort_cycle + 1) begin
            load_key(TEST_KEY, 0);
            @(negedge clk);
            start = 1;
            block_in = TEST_BLOCK;
            @(negedge clk);
            start = 0;
            repeat (abort_cycle-1) @(negedge clk);
            reset_core();
            repeat (24) @(negedge clk);
            if (key_valid || done || busy) $fatal(1, "Aborted encryption completed");
        end
        load_key(TEST_KEY, 0);
        encrypt_block(TEST_BLOCK, TEST_CIPHER);

        // Held start is a level handshake: exactly two accepted operations.
        @(negedge clk);
        before_count = completions;
        start = 1;
        block_in = TEST_BLOCK;
        for (step = 1; step <= 42; step = step + 1) begin
            @(posedge clk);
            #3;
            if (step == 21 || step == 42) begin
                if (!done || ciphertext !== TEST_CIPHER) $fatal(1, "Held-start result failed");
            end
            if (step == 22) begin
                @(negedge clk);
                start = 0;
            end
        end
        repeat (24) @(negedge clk);
        if (completions != before_count + 2 || busy || done)
            $fatal(1, "Held start completion count mismatch");
        $display("PASS aes128_core: %0d independent vectors; %0d total correct completions; %0d key preparations; reset at 28 stages; priority/busy/rekey/held-start", vector_count, completions, key_completions);
        $display("METRIC aes128_core clock_ns=20 key_cycles=10 block_cycles=20 initiation_cycles=%0d", min_interval);
        $finish;
    end
    initial begin
        #3000000;
        $fatal(1, "AES core watchdog timeout");
    end
endmodule

`default_nettype wire
