`timescale 1ns/1ps
`default_nettype none

// UART-only bench target for the Terasic DE10-Nano.
// 0x55 is transmitted every 100 ms at 9600 baud, 8N1, from the 50 MHz FPGA
// clock. KEY0_N resets the diagnostic. The LEDs keep the same useful pattern
// as the DE10-Lite scope target: LED0 is a heartbeat, LED1 records that a TX
// frame started, and LED[7:2] shows the upper six bits of the last RX byte.
module de10_nano_uart_scope_top (
    input  wire       FPGA_CLK1_50,
    input  wire       KEY0_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [7:0] LED
);
    reg [25:0] heartbeat_counter;
    wire heartbeat = heartbeat_counter[25];
    wire [7:0] last_rx_data;
    wire uart_reset_active;

    always @(posedge FPGA_CLK1_50 or posedge uart_reset_active) begin
        if (uart_reset_active)
            heartbeat_counter <= 26'd0;
        else
            heartbeat_counter <= heartbeat_counter + 1'b1;
    end

    uart_scope #(.CLK_FREQ(50_000_000), .BAUD_RATE(9600)) scope_inst (
        .clk(FPGA_CLK1_50), .arst(!KEY0_N), .rx(UART_RX), .tx(UART_TX),
        .last_rx_data(last_rx_data), .rx_seen(), .tx_seen(LED[1]),
        .error_sticky(), .reset_active(uart_reset_active)
    );

    assign LED[7:2] = last_rx_data[7:2];
    assign LED[0] = heartbeat;

endmodule

`default_nettype wire
