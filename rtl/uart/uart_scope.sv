`timescale 1ns/1ps
`default_nettype none

// Bench stimulus and diagnostics around the production UART RX/TX.
// TX sends TEST_BYTE every PERIOD_CYCLES clocks, independently of RX.
// Connect TX to RX with a physical jumper to exercise both GPIOs.
module uart_scope #(
    parameter integer CLK_FREQ = 50_000_000,
    parameter integer BAUD_RATE = 9600,
    parameter integer PERIOD_CYCLES = CLK_FREQ / 10,
    parameter [7:0] TEST_BYTE = 8'h55
) (
    input  wire       clk,
    input  wire       arst,
    input  wire       rx,
    output wire       tx,
    output wire [7:0] last_rx_data,
    output reg        rx_seen,
    output reg        error_sticky,
    output wire       reset_active
);
    localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;
    localparam integer TIMER_WIDTH = (PERIOD_CYCLES > 1) ? $clog2(PERIOD_CYCLES) : 1;
    localparam [TIMER_WIDTH-1:0] PERIOD_LAST = TIMER_WIDTH'(PERIOD_CYCLES - 1);
    reg [TIMER_WIDTH-1:0] period_timer;
    wire rst, tx_busy, unused_tx_done, rx_done, framing_error;
    wire tx_start = !rst && !tx_busy && (period_timer == 0);

`ifndef SYNTHESIS
    initial begin
        if (PERIOD_CYCLES <= 10 * CLKS_PER_BIT + 1)
            $fatal(1, "uart_scope period must exceed one full frame plus handshake");
    end
`endif

    reset_sync reset_inst (.clk(clk), .arst(arst), .rst(rst));
    assign reset_active = rst;
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) tx_inst (
        .clk(clk), .rst(rst), .tx_start(tx_start), .tx_data(TEST_BYTE),
        .tx(tx), .tx_busy(tx_busy), .tx_done(unused_tx_done)
    );
    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) rx_inst (
        .clk(clk), .rst(rst), .rx(rx), .rx_data(last_rx_data),
        .rx_done(rx_done), .rx_framing_error(framing_error)
    );

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            period_timer <= PERIOD_LAST;
            rx_seen <= 1'b0;
            error_sticky <= 1'b0;
        end else begin
            if (tx_start) period_timer <= PERIOD_LAST;
            else if (period_timer != 0) period_timer <= period_timer - 1'b1;
            if (rx_done) begin
                rx_seen <= 1'b1;
                if (last_rx_data != TEST_BYTE) error_sticky <= 1'b1;
            end
            if (framing_error) error_sticky <= 1'b1;
        end
    end
endmodule

`default_nettype wire
