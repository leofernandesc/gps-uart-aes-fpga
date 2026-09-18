`timescale 1ns/1ps
`default_nettype none

// DE10-Lite baseline: UART RX -> FIFO -> UART TX, without AES hardware.
module de10_lite_uart_baseline_top (
    input  wire       MAX10_CLK1_50,
    input  wire       KEY0_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [9:0] LEDR
);
    de10_lite_uart_ctr_top #(.ENABLE_AES(0)) implementation (
        .MAX10_CLK1_50 (MAX10_CLK1_50),
        .KEY0_N        (KEY0_N),
        .UART_RX       (UART_RX),
        .UART_TX       (UART_TX),
        .LEDR          (LEDR)
    );
endmodule

`default_nettype wire
