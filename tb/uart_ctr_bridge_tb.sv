`timescale 1ns/1ps
`default_nettype none

module uart_ctr_bridge_tb;
    parameter integer ENABLE_AES = 1;
    parameter integer CLK_FREQ = 307200;
    parameter integer FIFO_DEPTH = 8;
    parameter integer GPS_ONLY = 0;
    localparam integer CPB = CLK_FREQ / 9600;
    localparam integer BIT_NS = CPB * 20;
    localparam integer LW = $clog2(FIFO_DEPTH + 1);
    reg clk = 0;
    always #10 clk = !clk;
    reg rst = 1, rx = 1, tx_enable = 1, abort_req = 0, cfg_valid = 0;
    reg [127:0] cfg_key = 0;
    reg [95:0] cfg_nonce = 0;
    reg [31:0] cfg_counter = 0;
    wire tx, cfg_ready, cfg_done, active, exhausted, tx_busy, rx_event, tx_event;
    wire overflow_sticky, framing_sticky;
    wire [LW-1:0] fifo_level, fifo_high_water;
    uart_ctr_bridge #(.ENABLE_AES(ENABLE_AES), .CLK_FREQ(CLK_FREQ), .FIFO_DEPTH(FIFO_DEPTH)) dut (.*);

    reg [7:0] plain [0:4095];
    reg [7:0] expected [0:4095];
    integer decoded = 0, completed = 0, received = 0;
    integer case_id = 0, length = 0, epoch = 0, total_decoded = 0;
    integer capture, fixtures, count, fields, i, p, c, run_limit;
    integer first_case = 0, cases_run = 0;
    integer cfg_pulses = 0, fault_checks = 0, cancel_checks = 0;
    integer sim_cycle = 0;
    integer first_rx_cycle = -1, first_tx_cycle = -1, last_tx_cycle = -1;
    integer gps_fifo_high_water = 0;
    integer gps_rx_to_first_tx_cycles = 0, gps_rx_to_last_tx_cycles = 0;
    reg checking = 0;
    string run_name, run_speed;

    always @(posedge clk) begin
        sim_cycle = sim_cycle + 1;
        if (cfg_done) cfg_pulses = cfg_pulses + 1;
        if (checking && rx_event) begin
            received = received + 1;
            if (first_rx_cycle < 0) first_rx_cycle = sim_cycle;
        end
        if (checking && tx_event) begin
            completed = completed + 1;
            if (first_tx_cycle < 0) first_tx_cycle = sim_cycle;
            last_tx_cycle = sim_cycle;
        end
    end

    // Decoder observes the serial wire only, never DUT payload/mask registers.
    // Epoch invalidates a partial frame intentionally cancelled by reset/abort.
    initial begin : decoder
        integer seen_epoch, bit_index;
        reg [7:0] value;
        forever begin
            @(negedge tx);
            seen_epoch = epoch;
            #(BIT_NS / 2);
            if (checking && seen_epoch == epoch) begin
                if (tx !== 0) $fatal(1, "Invalid TX start bit");
                for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                    #(BIT_NS);
                    value[bit_index] = tx;
                end
                #(BIT_NS);
                if (checking && seen_epoch == epoch) begin
                    if (tx !== 1) $fatal(1, "Invalid TX stop bit");
                    if (decoded >= length) $fatal(1, "Unexpected extra TX byte");
                    if (value !== expected[decoded])
                        $fatal(1, "case=%0d offset=%0d got=%02x expected=%02x", case_id, decoded, value, expected[decoded]);
                    $fdisplay(capture, "%0d %0d %02x", case_id, decoded, value);
                    decoded = decoded + 1;
                    total_decoded = total_decoded + 1;
                end
            end
        end
    end

    task automatic ticks(input integer n);
        repeat (n) @(negedge clk);
    endtask

    task automatic cancel;
        @(negedge clk);
        checking = 0;
        epoch = epoch + 1;
        abort_req = 1;
        rx = 1;
        ticks(2);
        abort_req = 0;
        ticks(2);
        if (active || tx_busy || tx !== 1 || fifo_level != 0)
            $fatal(1, "Abort did not clear datapath");
    endtask

    task automatic configure;
        integer timeout_count;
        timeout_count = 0;
        while (!cfg_ready && timeout_count < 100) begin
            ticks(1);
            timeout_count = timeout_count + 1;
        end
        if (!cfg_ready) $fatal(1, "Configuration timeout");
        cfg_valid = 1;
        ticks(1);
        cfg_valid = 0;
        if (!active || cfg_ready) $fatal(1, "Configuration not accepted");
        // Key preparation may complete before the first mask. RX needs idle.
        ticks(CPB + 50);
    endtask

    task automatic send_frame(input reg [7:0] value, input reg bad_stop);
        integer bit_index;
        // Non-clock-aligned source, LSB first; spare idle cycles avoid a
        // fabricated infinite, 100%-duty source in the accelerated long test.
        @(negedge clk);
        #7 rx = 0;
        #(BIT_NS);
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
            rx = value[bit_index];
            #(BIT_NS);
        end
        rx = !bad_stop;
        #(BIT_NS);
        rx = 1;
        ticks(3);
    endtask

    task automatic await_drain;
        integer timeout_count;
        timeout_count = 0;
        while (completed < length && timeout_count < (length + 4) * 12 * CPB) begin
            ticks(1);
            timeout_count = timeout_count + 1;
        end
        if (decoded != length || completed != length || received != length)
            $fatal(1, "Drain mismatch RX=%0d TX=%0d done=%0d expected=%0d", received, decoded, completed, length);
        ticks(12 * CPB);
        if (tx_busy || fifo_level || overflow_sticky || framing_sticky)
            $fatal(1, "Datapath did not drain cleanly");
    endtask

    initial begin : stimulus
        integer pass_cfg;
        fixtures = $fopen("build/integration/vectors.txt", "r");
        if (ENABLE_AES) run_name = "secure";
        else run_name = "baseline";
        if (CLK_FREQ == 50000000) begin
            if (GPS_ONLY) run_speed = "50mhz-gps";
            else run_speed = "50mhz";
        end
        else run_speed = "fast";
        capture = $fopen($sformatf("build/integration/%s-%s.txt", run_name, run_speed), "w");
        if (!fixtures || !capture) $fatal(1, "Cannot open integration fixtures/output");
        fields = $fscanf(fixtures, "%d\n", count);
        if (fields != 1) $fatal(1, "Missing fixture count");
        // The final fixture is reserved for byte-exact recovery after faults.
        // GPS_ONLY selects the public NMEA replay (fixture 4) at the real
        // 50 MHz/9600 baud timing without repeating the preceding short cases.
        if (GPS_ONLY) begin
            if (count <= 4) $fatal(1, "GPS replay fixture is missing");
            first_case = 4;
            run_limit = 5;
        end else if (CLK_FREQ == 50000000) begin
            first_case = 0;
            run_limit = 4;
        end else begin
            first_case = 0;
            run_limit = count - 1;
        end
        cases_run = run_limit - first_case;
        ticks(5);
        rst = 0;
        ticks(CPB + 5);

        // RX before configuration is ignored, including a complete frame.
        send_frame(8'hcc, 0);
        if (tx_busy || fifo_level || active) $fatal(1, "Unconfigured RX leaked");

        for (case_id = 0; case_id < run_limit; case_id = case_id + 1) begin
            cancel();
            fields = $fscanf(fixtures, "%h %h %h %d\n", cfg_key, cfg_nonce, cfg_counter, length);
            if (fields != 4 || length > 4096) $fatal(1, "Invalid fixture header");
            for (i = 0; i < length; i = i + 1) begin
                fields = $fscanf(fixtures, "%h %h\n", p, c);
                if (fields != 2) $fatal(1, "Invalid fixture byte");
                plain[i] = p[7:0];
                expected[i] = ENABLE_AES ? c[7:0] : p[7:0];
            end
            if (case_id < first_case) continue;
            decoded = 0;
            completed = 0;
            received = 0;
            first_rx_cycle = -1;
            first_tx_cycle = -1;
            last_tx_cycle = -1;
            tx_enable = 1;
            configure();
            checking = 1;
            // A valid pulse while active must not replace the key/context.
            pass_cfg = cfg_pulses;
            cfg_valid = 1;
            ticks(3);
            cfg_valid = 0;
            if (cfg_pulses != pass_cfg || cfg_ready) $fatal(1, "Live reconfiguration accepted");
            for (i = 0; i < length; i = i + 1) begin
                // Hold the first three bytes across FIFO synchronous reads,
                // then pause a later byte while TX is already in progress.
                if (!GPS_ONLY && i == 0) tx_enable = 0;
                send_frame(plain[i], 0);
                if (!GPS_ONLY && (i == 2 || i == length - 1)) begin
                    ticks(2 * CPB);
                    if (decoded != 0 && i <= 2) $fatal(1, "TX ignored pause");
                    tx_enable = 1;
                end
                if (!GPS_ONLY && i == 8) begin
                    tx_enable = 0;
                    ticks(13 * CPB);
                    if (tx_busy) $fatal(1, "TX started another byte while paused");
                    ticks(2 * CPB);
                    tx_enable = 1;
                end
            end
            await_drain();
            if (GPS_ONLY) begin
                if (first_rx_cycle < 0 || first_tx_cycle < 0 || last_tx_cycle < 0)
                    $fatal(1, "GPS replay timing markers were not observed");
                gps_fifo_high_water = fifo_high_water;
                gps_rx_to_first_tx_cycles = first_tx_cycle - first_rx_cycle;
                gps_rx_to_last_tx_cycles = last_tx_cycle - first_rx_cycle;
            end
            if (cfg_counter == 32'hffffffff && ENABLE_AES) begin
                if (!exhausted) $fatal(1, "Counter exhaustion not reported");
                send_frame(8'h99, 0);
                ticks(24 * CPB);
                if (decoded != length || tx_busy) $fatal(1, "Counter wrapped");
                fault_checks = fault_checks + 1;
            end
        end
        checking = 0;

        if (CLK_FREQ != 50000000) begin
            // Stop-bit error invalidates capture and blocks configuration until
            // explicit abort. No stale FIFO/TX data may survive recovery.
            cancel();
            cfg_counter = 0;
            cfg_nonce = cfg_nonce + 1;
            configure();
            send_frame(8'ha5, 1);
            ticks(3 * CPB);
            if (!framing_sticky || active || cfg_ready || tx_busy || tx !== 1)
                $fatal(1, "Framing error did not stop capture");
            fault_checks = fault_checks + 1;

            cancel();
            cfg_nonce = cfg_nonce + 1;
            configure();
            tx_enable = 0;
            for (i = 0; i < FIFO_DEPTH + 2; i = i + 1) send_frame(8'(i), 0);
            ticks(CPB);
            if (!overflow_sticky || active || cfg_ready || tx_busy || fifo_high_water != LW'(FIFO_DEPTH))
                $fatal(1, "Overflow did not latch/stop capture/high-water");
            fault_checks = fault_checks + 1;

            // Sweep cancellation across key expansion/mask preparation; abort
            // and reset also cancel a serial frame partway through transmission.
            for (i = 0; i < 24; i = i + 1) begin
                cancel();
                cfg_nonce = cfg_nonce + 1;
                while (!cfg_ready) ticks(1);
                cfg_valid = 1;
                ticks(1);
                cfg_valid = 0;
                ticks(i);
                cancel();
                if (tx_busy || tx !== 1) $fatal(1, "Cancelled setup leaked output");
                cancel_checks = cancel_checks + 1;
            end
            for (i = 0; i < 2; i = i + 1) begin
                cfg_nonce = cfg_nonce + 1;
                tx_enable = 1;
                configure();
                // Sending RX and waiting for TX concurrently targets the frame
                // itself, not just an empty pipeline after a completed byte.
                fork
                    send_frame(8'h00, 0);
                    begin
                        @(negedge tx);
                        ticks(2 * CPB);
                        if (i == 0) cancel();
                        else begin
                            rst = 1;
                            epoch = epoch + 1;
                            ticks(3);
                            rst = 0;
                        end
                    end
                join
                ticks(12 * CPB);
                if (tx_busy || tx !== 1 || fifo_level || active)
                    $fatal(1, "Cancelled TX did not return idle");
                cancel_checks = cancel_checks + 1;
            end
            // Abort at/around the FIFO read response with TX deliberately
            // stalled, covering reservation and retention of an unread byte.
            for (i = 0; i < 6; i = i + 1) begin
                cfg_nonce = cfg_nonce + 1;
                configure();
                tx_enable = 0;
                fork
                    send_frame(8'hff, 0);
                    begin
                        @(posedge rx_event);
                        ticks(i + 1);
                        cancel();
                    end
                join
                cancel_checks = cancel_checks + 1;
            end
            // Byte-exact recovery with a fresh independent-library fixture.
            fields = $fscanf(fixtures, "%h %h %h %d\n", cfg_key, cfg_nonce, cfg_counter, length);
            if (fields != 4) $fatal(1, "Missing recovery fixture");
            for (i = 0; i < length; i = i + 1) begin
                fields = $fscanf(fixtures, "%h %h\n", p, c);
                if (fields != 2) $fatal(1, "Missing recovery byte");
                plain[i] = p[7:0];
                expected[i] = ENABLE_AES ? c[7:0] : p[7:0];
            end
            decoded = 0;
            completed = 0;
            received = 0;
            tx_enable = 1;
            configure();
            checking = 1;
            for (i = 0; i < length; i = i + 1) send_frame(plain[i], 0);
            await_drain();
            cases_run = cases_run + 1;
        end
        cancel();
        $fclose(fixtures);
        $fclose(capture);
        $display("PASS UART integration AES=%0d clock=%0d cases=%0d serial_bytes=%0d faults=%0d cancellations=%0d",
                 ENABLE_AES, CLK_FREQ, cases_run, total_decoded, fault_checks, cancel_checks);
        if (GPS_ONLY)
            $display("METRIC GPS AES=%0d bytes=%0d fifo_high_water=%0d rx_to_first_tx_cycles=%0d rx_to_last_tx_cycles=%0d",
                     ENABLE_AES, total_decoded, gps_fifo_high_water,
                     gps_rx_to_first_tx_cycles, gps_rx_to_last_tx_cycles);
        $finish;
    end

    initial begin
        #2000000000;
        $fatal(1, "Integration watchdog");
    end
endmodule

`default_nettype wire
