`timescale 1ns/1ps
`default_nettype none

// Fixed production setting: 50 MHz / 9600 baud, 8N1. Press KEY0 after loading.
// GPIO locations and LED meanings are documented in README.md in this folder.
module de10_lite_uart_top (
    input  wire       MAX10_CLK1_50,
    input  wire       KEY0_N,
    input  wire       GPS_RX,
    output wire       UART_TX,
    output wire [9:0] LEDR
);
    wire rst, tx_busy, rx_event, tx_event, overflow_sticky, framing_sticky;
    wire [10:0] fifo_level, fifo_high_water;
    reg rx_toggle, tx_toggle;

    reset_sync reset_inst (.clk(MAX10_CLK1_50), .arst(!KEY0_N), .rst(rst));
    uart_bridge bridge_inst (
        .clk(MAX10_CLK1_50), .rst(rst), .rx(GPS_RX), .tx_enable(1'b1),
        .tx(UART_TX), .tx_busy(tx_busy), .rx_event(rx_event), .tx_event(tx_event),
        .overflow_sticky(overflow_sticky), .framing_sticky(framing_sticky),
        .fifo_level(fifo_level), .fifo_high_water(fifo_high_water)
    );

    always @(posedge MAX10_CLK1_50 or posedge rst) begin
        if (rst) begin
            rx_toggle <= 1'b0;
            tx_toggle <= 1'b0;
        end else begin
            if (rx_event) rx_toggle <= !rx_toggle;
            if (tx_event) tx_toggle <= !tx_toggle;
        end
    end

    assign LEDR[0] = !rst;
    assign LEDR[1] = rx_toggle;
    assign LEDR[2] = tx_toggle;
    assign LEDR[3] = (fifo_level != 0);
    assign LEDR[4] = tx_busy;
    assign LEDR[5] = (fifo_level == 11'd1024);
    assign LEDR[6] = overflow_sticky;
    assign LEDR[7] = framing_sticky;
    assign LEDR[8] = (fifo_high_water >= 11'd512);
    assign LEDR[9] = (fifo_high_water == 11'd1024);
endmodule

`default_nettype wire
