`timescale 1ns/1ps
`default_nettype none

module uart_bridge_tb #(
    parameter integer CLK_FREQ = 307200,
    parameter integer FIFO_DEPTH = 8,
    parameter integer STRESS = 1
);
    localparam integer LEVEL_WIDTH = $clog2(FIFO_DEPTH + 1);
    localparam integer CPB = CLK_FREQ / 9600;
    localparam realtime BIT_NS = (1.0 * CLK_FREQ / 9600) * 20.0;
    reg clk = 0;
    always #10 clk = ~clk;
    reg arst = 1, rx = 1, tx_enable = 1;
    wire rst, tx, tx_busy, rx_event, tx_event, overflow_sticky, framing_sticky;
    wire [LEVEL_WIDTH-1:0] fifo_level, fifo_high_water;
    reset_sync reset_inst (.clk(clk), .arst(arst), .rst(rst));
    uart_bridge #(.CLKS_PER_BIT(CPB), .FIFO_DEPTH(FIFO_DEPTH)) dut (.*);

    reg [7:0] expected [0:8191];
    integer queued = 0, decoded = 0, completed = 0, received = 0;
    integer epoch = 0, total_decoded = 0, n;
    // Synthetic transport stimulus, not a GPS capture or a claim of GPS fix.
    string nmea = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n";

    always @(posedge clk) begin
        #1;
        if (!rst) begin
            if (rx_event) received = received + 1;
            if (tx_event) completed = completed + 1;
        end
    end

    // Independent PC-side serial decoder. Only physical TX and reset are read.
    initial begin : serial_decoder
        integer bit_number, start_epoch;
        reg [7:0] observed;
        forever begin
            @(negedge tx);
            start_epoch = epoch;
            #(BIT_NS / 2.0);
            if (!rst && start_epoch == epoch && tx !== 0)
                $fatal(1, "Bridge TX start too short");
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                #(BIT_NS);
                observed[bit_number] = tx;
            end
            #(BIT_NS);
            if (!rst && start_epoch == epoch) begin
                if (tx !== 1) $fatal(1, "Bridge TX invalid stop");
                if (decoded >= queued || observed !== expected[decoded])
                    $fatal(1, "Bridge byte %0d got=%02x expected=%02x queued=%0d", decoded, observed, expected[decoded], queued);
                decoded = decoded + 1;
                total_decoded = total_decoded + 1;
            end
        end
    end

    task automatic send_frame(input reg [7:0] data, input reg stop_ok, input reg expect_forward);
        integer b;
        begin
            if (expect_forward) begin
                expected[queued] = data;
                queued = queued + 1;
            end
            rx = 0;
            #(BIT_NS);
            for (b = 0; b < 8; b = b + 1) begin
                rx = data[b];
                #(BIT_NS);
            end
            rx = stop_ok;
            #(BIT_NS);
        end
    endtask

    task automatic drain;
        integer attempts;
        begin
            attempts = 0;
            while ((completed < queued || tx_busy || fifo_level != 0) && attempts < 20 * (FIFO_DEPTH + 4)) begin
                #(BIT_NS);
                attempts = attempts + 1;
            end
            #(12 * BIT_NS);
            if (decoded != queued || completed != queued || fifo_level != 0 || tx_busy)
                $fatal(1, "Bridge drain mismatch queued=%0d decoded=%0d completed=%0d", queued, decoded, completed);
        end
    endtask

    task automatic reset_bridge;
        begin
            #3;
            arst = 1;
            rx = 1;
            tx_enable = 1;
            epoch = epoch + 1;
            #1;
            if (tx !== 1 || tx_busy !== 0 || overflow_sticky !== 0 || framing_sticky !== 0 || fifo_level !== 0 || fifo_high_water !== 0)
                $fatal(1, "Bridge reset failed");
            queued = 0;
            decoded = 0;
            completed = 0;
            received = 0;
            #71;
            arst = 0;
            #(14 * BIT_NS);
        end
    endtask

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/uart_bridge.vcd");
            $dumpvars(0, uart_bridge_tb);
        end
        #37;
        reset_bridge();
        #7;
        for (n = 0; n < nmea.len(); n = n + 1) send_frame(nmea[n], 1, 1);
        for (n = 0; n < (STRESS ? 256 : 16); n = n + 1) send_frame(8'(n), 1, 1);
        drain();
        if (overflow_sticky || framing_sticky || received != queued)
            $fatal(1, "Bridge clean stream error");

        // Pause internal consumption, then release the exact queued bytes.
        tx_enable = 0;
        for (n = 0; n < 4; n = n + 1) send_frame(8'(n) ^ 8'ha0, 1, 1);
        #(2 * BIT_NS);
        if (fifo_level != 4 || tx_busy) $fatal(1, "Bridge pause failed");
        tx_enable = 1;
        drain();

        if (STRESS) begin
            tx_enable = 0;
            for (n = 0; n < FIFO_DEPTH + 3; n = n + 1)
                send_frame(8'(n) ^ 8'h50, 1, n < FIFO_DEPTH);
            #(2 * BIT_NS);
            if (!overflow_sticky || fifo_level != FIFO_DEPTH || fifo_high_water != FIFO_DEPTH)
                $fatal(1, "Bridge overflow not diagnosed");
            tx_enable = 1;
            drain();
            if (!overflow_sticky) $fatal(1, "Overflow indication did not latch");
        end

        // An invalid frame is never queued. Continuous break stays silent.
        send_frame(8'hd3, 0, 0);
        #(24 * BIT_NS);
        if (!framing_sticky) $fatal(1, "Missing framing diagnostic");
        rx = 1;
        #(2 * BIT_NS);
        send_frame(8'h39, 1, 1);
        drain();

        // Reset with queued bytes and one incomplete TX: no stale data after reset.
        tx_enable = 0;
        for (n = 0; n < 4; n = n + 1) send_frame(8'hc0 + 8'(n), 1, 1);
        tx_enable = 1;
        @(negedge tx);
        #(2 * BIT_NS + 3);
        reset_bridge();
        send_frame(8'h7e, 1, 1);
        drain();
        if (overflow_sticky || framing_sticky || received != 1)
            $fatal(1, "Bridge recovery failed");
        $display("PASS uart_bridge CLK_FREQ=%0d DEPTH=%0d: %0d decoded bytes; synthetic NMEA; pause/order; framing; reset; overflow_stress=%0d", CLK_FREQ, FIFO_DEPTH, total_decoded, STRESS);
        $finish;
    end

    initial begin
        #(BIT_NS * 30000);
        $fatal(1, "Bridge watchdog timeout");
    end
endmodule

`default_nettype wire
