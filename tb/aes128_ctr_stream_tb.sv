`timescale 1ns/1ps
`default_nettype none

module aes128_ctr_stream_tb;
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst = 1, abort_req = 0, cfg_valid = 0, in_valid = 0, out_ready = 0;
    reg [127:0] cfg_key = 0;
    reg [95:0] cfg_nonce = 0;
    reg [31:0] cfg_counter = 0;
    reg [7:0] in_data = 0;
    wire cfg_ready, cfg_done, active, exhausted, in_ready, out_valid;
    wire [7:0] out_data;
    aes128_ctr_stream dut (.*);

    localparam [127:0] KEY = 128'h2b7e151628aed2a6abf7158809cf4f3c;
    localparam [95:0] NONCE = 96'hf0f1f2f3f4f5f6f7f8f9fafb;
    localparam [31:0] COUNTER = 32'hfcfdfeff;
    reg [7:0] source [0:8191];
    reg [7:0] expected [0:8191];
    integer cycles = 0, accepted_at = 0, stalls_seen = 0, total_bytes = 0;
    integer cold_latency = -1;
    reg stalled = 0;
    reg [7:0] held_output = 0;
    always @(posedge clk) begin
        cycles = cycles + 1;
        if (rst || abort_req) stalled = 0;
        else begin
            if ((^{cfg_ready,cfg_done,active,exhausted,in_ready,out_valid}) === 1'bx)
                $fatal(1, "CTR stream unknown control");
            if (stalled && (!out_valid || out_data !== held_output))
                $fatal(1, "CTR ciphertext changed while stalled");
            if ((in_valid && in_ready) !== (out_valid && out_ready))
                $fatal(1, "CTR input/output transfers do not match");
            if (exhausted && (out_valid || in_ready)) $fatal(1, "Transfer after exhaustion");
            stalled = out_valid && !out_ready;
            held_output = out_data;
            if (stalled) stalls_seen = stalls_seen + 1;
        end
    end

    task automatic clear_context(input reg reset_all);
        begin
            @(negedge clk);
            if (reset_all) begin
                #3;
                rst = 1;
            end else abort_req = 1;
            cfg_valid = 1;
            in_valid = 0;
            #1;
            if (cfg_ready || in_ready || out_valid) $fatal(1, "Abort/reset did not suppress transfer");
            repeat (2) @(negedge clk);
            abort_req = 0;
            rst = 0;
            cfg_valid = 0;
            #1;
            if (active || exhausted || out_valid || in_ready) $fatal(1, "Context not cleared");
        end
    endtask

    task automatic configure(input reg [127:0] key, input reg [95:0] nonce,
                             input reg [31:0] counter);
        integer waiting;
        begin
            waiting = 0;
            @(negedge clk);
            while (!cfg_ready) begin
                @(negedge clk);
                waiting = waiting + 1;
                if (waiting > 25) $fatal(1, "AES did not drain after abort");
            end
            cfg_key = key;
            cfg_nonce = nonce;
            cfg_counter = counter;
            cfg_valid = 1;
            @(posedge clk);
            #1;
            accepted_at = cycles;
            if (!active || cfg_ready) $fatal(1, "CTR configuration handshake failed");
            @(negedge clk);
            cfg_valid = 0;
            cfg_key = ~key;
            cfg_nonce = ~nonce;
            cfg_counter = ~counter;
        end
    endtask

    task automatic fresh_byte;
        integer waiting;
        begin
            configure(KEY, NONCE, COUNTER);
            in_valid = 1;
            in_data = 8'h6b;
            out_ready = 1;
            waiting = 0;
            begin : wait_byte
                forever begin
                    @(posedge clk);
                    if (in_ready) begin
                        if (!out_valid || out_data !== 8'h87) $fatal(1, "Stale mask after rearm");
                        disable wait_byte;
                    end
                    waiting = waiting + 1;
                    if (waiting > 40) $fatal(1, "Fresh context timeout");
                end
            end
            @(negedge clk);
            in_valid = 0;
            clear_context(0);
        end
    endtask

    integer fd, result_fd, count, n, j, length, schedule, terminal, scan;
    integer index, elapsed, phase, reset_kind, cfg_pulses;
    reg [127:0] key;
    reg [95:0] nonce;
    reg [31:0] initial_counter;
    reg transferred;
    initial begin
        #1;
        rst = 0;
        #1;
        rst = 1;
        clear_context(1);
        in_valid = 1;
        out_ready = 1;
        repeat (6) begin
            @(posedge clk);
            if (in_ready || out_valid) $fatal(1, "Data accepted before configuration");
        end
        @(negedge clk);
        in_valid = 0;
        fd = $fopen("build/ctr/stream-vectors.txt", "r");
        result_fd = $fopen("build/ctr/rtl-bytes.txt", "w");
        if (!fd || !result_fd || $fscanf(fd, "%d\n", count) != 1 || count < 1)
            $fatal(1, "Missing CTR stream vectors");
        for (n = 0; n < count; n = n + 1) begin
            scan = $fscanf(fd, "%h %h %h %d %d %d\n", key, nonce, initial_counter, length, schedule, terminal);
            if (scan != 6 || length < 1 || length > 8192) $fatal(1, "Malformed CTR stream header");
            for (j = 0; j < length; j = j + 1) begin
                scan = $fscanf(fd, "%h %h\n", source[j], expected[j]);
                if (scan != 2) $fatal(1, "Malformed CTR stream byte");
            end
            clear_context(n % 2 == 0);
            configure(key, nonce, initial_counter);
            index = 0;
            elapsed = 0;
            transferred = 0;
            cfg_pulses = 0;
            while (index < length) begin
                @(negedge clk);
                if (transferred) in_valid = 0;
                if (!in_valid && (schedule == 0 ||
                    (schedule == 1 && elapsed % 7 != 1) ||
                    (schedule == 2 && elapsed % 53 == 0))) begin
                    in_valid = 1;
                    in_data = source[index];
                end
                out_ready = schedule == 0 ||
                            (elapsed > 130 && elapsed % 97 > 29 && elapsed % 5 != 0);
                // Configuration changes must be ignored until explicitly aborted.
                cfg_valid = elapsed % 11 == 0;
                @(posedge clk);
                if (cfg_done) cfg_pulses = cfg_pulses + 1;
                transferred = in_valid && in_ready;
                if (transferred) begin
                    if (out_data !== expected[index])
                        $fatal(1, "CTR byte mismatch session=%0d byte=%0d actual=%02x expected=%02x",
                               n, index, out_data, expected[index]);
                    $fdisplay(result_fd, "%0d %0d %02x", n, index, out_data);
                    index = index + 1;
                    total_bytes = total_bytes + 1;
                end
                elapsed = elapsed + 1;
                if (elapsed > length * 300 + 300) $fatal(1, "CTR stream timeout");
                #1;
                if (n == 0 && index == 1 && cold_latency < 0) cold_latency = cycles - accepted_at;
            end
            @(negedge clk);
            in_valid = 0;
            cfg_valid = 0;
            out_ready = 1;
            if (cfg_pulses != 1) $fatal(1, "Key expansion completion count incorrect");
            repeat (70) begin
                @(posedge clk);
                #1;
                if (out_valid) $fatal(1, "Unexpected extra output byte");
                if (exhausted !== 1'(terminal)) $fatal(1, "CTR premature/missing exhaustion");
            end
            if (terminal) begin
                @(negedge clk);
                in_valid = 1;
                in_data = 8'hff;
                repeat (40) begin
                    @(posedge clk);
                    if (in_ready || out_valid || !exhausted) $fatal(1, "CTR counter wrapped");
                end
            end
        end
        $fclose(fd);
        $fclose(result_fd);

        // Abort/reset in every startup phase, including AES busy and a stalled
        // output. Each cancellation is followed by an
        // independently known first byte to detect late/stale AES completions.
        for (reset_kind = 0; reset_kind < 2; reset_kind = reset_kind + 1) begin
            for (phase = 0; phase < 70; phase = phase + 1) begin
                clear_context(0);
                configure(~KEY, ~NONCE, 32'hffffffff);
                out_ready = 0;
                in_valid = 1;
                in_data = 8'h13;
                repeat (phase) @(negedge clk);
                clear_context(1'(reset_kind));
                fresh_byte();
            end
        end
        if (stalls_seen < 100 || cold_latency != 34) $fatal(1, "CTR coverage/startup latency failed");
        $display("PASS aes128_ctr_stream: %0d streams; %0d bytes; %0d stalled cycles; 140 abort/reset phases; partial blocks; no wrap",
                 count, total_bytes, stalls_seen);
        $display("METRIC ctr_stream clock_ns=20 config_to_first_transfer_cycles=%0d", cold_latency);
        $finish;
    end
    initial begin
        #100000000;
        $fatal(1, "CTR stream watchdog");
    end
endmodule

`default_nettype wire
