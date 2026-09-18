`timescale 1ns/1ps
`default_nettype none

// 0x55 every 100 ms, 9600 8N1. KEY0 clears the test and restarts the timer.
// LED0 = board/clock heartbeat; LED[7:1] = upper seven bits of last RX byte;
// LED8 = byte received; LED9 = error since reset.
module de10_lite_uart_scope_top (
    input  wire       MAX10_CLK1_50,
    input  wire       KEY0_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [9:0] LEDR
);
    reg [25:0] heartbeat_counter;
    wire heartbeat = heartbeat_counter[25];
    wire [7:0] last_rx_data;
    wire uart_reset_active;

    // Independent visual diagnostic.  It must toggle even when UART_RX is
    // disconnected, so a dark LED bank can be distinguished from a failed
    // UART loopback.  KEY0_N is the board's active-low push-button.
    always @(posedge MAX10_CLK1_50 or posedge uart_reset_active) begin
        if (uart_reset_active)
            heartbeat_counter <= 26'd0;
        else
            heartbeat_counter <= heartbeat_counter + 1'b1;
    end

    uart_scope #(.CLK_FREQ(50_000_000), .BAUD_RATE(9600)) scope_inst (
        .clk(MAX10_CLK1_50), .arst(!KEY0_N), .rx(UART_RX), .tx(UART_TX),
        .last_rx_data(last_rx_data), .rx_seen(LEDR[8]),
        .error_sticky(LEDR[9]), .reset_active(uart_reset_active)
    );

    assign LEDR[7:1] = last_rx_data[7:1];
    assign LEDR[0] = heartbeat;
endmodule

`default_nettype wire
