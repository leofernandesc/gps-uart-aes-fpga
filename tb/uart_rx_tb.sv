`timescale 1ns/1ps
`default_nettype none

module uart_rx_tb #(
    parameter integer CLKS_PER_BIT = 32
);
    localparam time CLOCK_NS = 20;
    localparam time BIT_NS = CLKS_PER_BIT * CLOCK_NS;
    reg clk = 1'b0;
    always #(CLOCK_NS / 2) clk = ~clk;
    reg rst = 1'b1;
    reg rx = 1'b1;
    wire [7:0] rx_data;
    wire rx_done, rx_framing_error;

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) dut (.*);

    reg [7:0] expected [0:8191];
    integer queued = 0, received = 0, framing_errors = 0;
    integer phase, value, before_errors, before_received;
    reg previous_done = 0, previous_error = 0;
    reg [7:0] previous_data = 0;

    // The oracle observes only public outputs, never DUT timers/state.
    always @(posedge clk) begin
        #1;
        if (rst) begin
            if (rx_done !== 0 || rx_framing_error !== 0 || rx_data !== 0)
                $fatal(1, "RX outputs not cleared by reset");
            previous_done = 0;
            previous_error = 0;
            previous_data = 0;
        end else begin
            if (rx_done === 1'bx || rx_framing_error === 1'bx)
                $fatal(1, "RX has unknown status");
            if ((rx_done && previous_done) || (rx_framing_error && previous_error))
                $fatal(1, "RX status must pulse for exactly one clock");
            if (rx_done && rx_framing_error)
                $fatal(1, "RX accepted a frame marked invalid");
            if (rx_done) begin
                if (received >= queued)
                    $fatal(1, "Unexpected RX byte %02x", rx_data);
                if (rx_data !== expected[received])
                    $fatal(1, "RX byte %0d: got %02x expected %02x", received, rx_data, expected[received]);
                received = received + 1;
            end else if (rx_data !== previous_data) begin
                $fatal(1, "rx_data changed without rx_done");
            end
            if (rx_framing_error) framing_errors = framing_errors + 1;
            previous_done = rx_done;
            previous_error = rx_framing_error;
            previous_data = rx_data;
        end
    end

    // Independent asynchronous serial source: absolute time, not clk/baud_tick.
    task automatic send_frame(input reg [7:0] data, input time period_ns, input reg stop_high);
        integer bit_number;
        begin
            rx = 0;
            #(period_ns);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                rx = data[bit_number];
                #(period_ns);
            end
            rx = stop_high;
            #(period_ns);
        end
    endtask

    task automatic send_good(input reg [7:0] data, input time period_ns);
        begin
            expected[queued] = data;
            queued = queued + 1;
            send_frame(data, period_ns, 1'b1);
        end
    endtask

    task automatic check_drained;
        begin
            #(2 * BIT_NS);
            if (received != queued)
                $fatal(1, "Lost RX data: queued=%0d received=%0d", queued, received);
        end
    endtask

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/uart_rx.vcd");
            $dumpvars(0, uart_rx_tb);
        end
        #73;
        rst = 0;
        #(2 * BIT_NS);

        // Every byte at 20 distinct phases within a 20 ns system clock.
        // Within each sweep there is only the required stop bit between frames.
        for (phase = 0; phase < 20; phase = phase + 1) begin
            @(negedge clk);
            #(phase + 1);
            for (value = 0; value < 256; value = value + 1)
                send_good(8'(value), BIT_NS);
            check_drained();
        end

        // Oscillator mismatch is a robustness test, not another board setting.
        for (value = 0; value < 256; value = value + 1)
            send_good(8'(value), BIT_NS * 98 / 100);
        check_drained();
        for (value = 0; value < 256; value = value + 1)
            send_good(8'(255 - value), BIT_NS * 102 / 100);
        check_drained();
        if (framing_errors != 0) $fatal(1, "Valid frames caused errors");

        // Short false starts must neither deliver bytes nor signal a stop error.
        before_received = received;
        for (value = 0; value < 16; value = value + 1) begin
            rx = 0;
            #(BIT_NS / 4);
            rx = 1;
            #(2 * BIT_NS);
        end
        #(12 * BIT_NS);
        if (received != before_received || framing_errors != 0)
            $fatal(1, "False start accepted");
        send_good(8'hc3, BIT_NS);
        check_drained();

        // Bad stop + continuous break: one explicit error, no phantom bytes.
        before_errors = framing_errors;
        send_frame(8'h5a, BIT_NS, 1'b0);
        #(24 * BIT_NS);
        if (framing_errors != before_errors + 1)
            $fatal(1, "Break must yield one framing error, got %0d", framing_errors - before_errors);
        rx = 1;
        #(2 * BIT_NS);
        send_good(8'h3c, BIT_NS);
        check_drained();

        // Reset aborts an incomplete frame. Staying low after reset is not data.
        rx = 0;
        #(3 * BIT_NS + 7);
        rst = 1;
        #(2 * BIT_NS + 3);
        rst = 0;
        #(12 * BIT_NS);
        if (framing_errors != before_errors + 1)
            $fatal(1, "RX rearmed on a low line after reset");
        rx = 1;
        #(2 * BIT_NS);
        send_good(8'ha6, BIT_NS);
        check_drained();

        $display("PASS uart_rx CPB=%0d: %0d bytes; 20 phases; back-to-back; skew; false starts; framing/break; reset", CLKS_PER_BIT, received);
        $finish;
    end

    initial begin
        #(BIT_NS * 70000);
        $fatal(1, "RX watchdog timeout");
    end
endmodule

`default_nettype wire
