`timescale 1ns/1ps
`default_nettype none

// Autonomous UART bring-up for the ZRTech/WXEDA board profile.
// Sends 0x55 every 100 ms at 48 MHz, 9600 baud, 8N1.
module cyclone4_uart_scope_top (
    input  wire       CLOCK_48,
    input  wire       RESET_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [3:0] LED
);
    reg [25:0] heartbeat_counter;
    wire [7:0] last_rx_data;
    wire reset_active;
    wire rx_seen;
    wire tx_seen;
    wire error_sticky;

    always @(posedge CLOCK_48 or posedge reset_active) begin
        if (reset_active)
            heartbeat_counter <= 26'd0;
        else
            heartbeat_counter <= heartbeat_counter + 1'b1;
    end

    uart_scope #(
        .CLK_FREQ  (48_000_000),
        .BAUD_RATE (9600)
    ) scope_inst (
        .clk           (CLOCK_48),
        .arst         (!RESET_N),
        .rx           (UART_RX),
        .tx           (UART_TX),
        .last_rx_data (last_rx_data),
        .rx_seen      (rx_seen),
        .tx_seen      (tx_seen),
        .error_sticky (error_sticky),
        .reset_active (reset_active)
    );

    // Active-low board LEDs: heartbeat, TX seen, RX seen, error.
    assign LED[0] = ~heartbeat_counter[25];
    assign LED[1] = ~tx_seen;
    assign LED[2] = ~rx_seen;
    assign LED[3] = ~error_sticky;
endmodule

`default_nettype wire
