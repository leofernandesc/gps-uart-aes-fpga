`timescale 1ns/1ps
`default_nettype none

// DE10-Lite secure build: UART RX -> FIFO -> AES-128-CTR -> UART TX.
module de10_lite_uart_secure_top #(
    parameter [127:0] CONTEXT_KEY =
        de10_lite_context_pkg::CONTEXT_KEY,
    parameter [95:0] CONTEXT_NONCE =
        de10_lite_context_pkg::CONTEXT_NONCE,
    parameter [31:0] CONTEXT_COUNTER =
        de10_lite_context_pkg::CONTEXT_COUNTER
) (
    input  wire       MAX10_CLK1_50,
    input  wire       KEY0_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [9:0] LEDR
);
    de10_lite_uart_ctr_top #(
        .ENABLE_AES      (1),
        .CONTEXT_KEY     (CONTEXT_KEY),
        .CONTEXT_NONCE   (CONTEXT_NONCE),
        .CONTEXT_COUNTER (CONTEXT_COUNTER)
    ) implementation (
        .MAX10_CLK1_50 (MAX10_CLK1_50),
        .KEY0_N        (KEY0_N),
        .UART_RX       (UART_RX),
        .UART_TX       (UART_TX),
        .LEDR          (LEDR)
    );
endmodule

`default_nettype wire
