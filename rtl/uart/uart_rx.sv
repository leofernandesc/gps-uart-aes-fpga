`timescale 1ns/1ps
`default_nettype none

// 8N1 receiver. Two input synchronizer stages; one sample at each bit centre.
// No dependency on TX timing, a shared baud tick, or a generated clock.
module uart_rx #(
    parameter integer CLKS_PER_BIT = 5208
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       rx,
    output reg  [7:0] rx_data,
    output reg        rx_done,
    output reg        rx_framing_error
);
    localparam integer COUNT_WIDTH = (CLKS_PER_BIT > 1) ? $clog2(CLKS_PER_BIT) : 1;
    localparam [COUNT_WIDTH-1:0] BIT_LAST = COUNT_WIDTH'(CLKS_PER_BIT - 1);
    localparam [COUNT_WIDTH-1:0] HALF_LAST = COUNT_WIDTH'(CLKS_PER_BIT / 2 - 1);
    localparam [2:0] WAIT_IDLE = 3'd0, IDLE = 3'd1, START = 3'd2,
                     DATA = 3'd3, STOP = 3'd4;

    (* preserve *) reg rx_meta;
    (* preserve *) reg rx_sync;
    reg [2:0] state;
    reg [COUNT_WIDTH-1:0] bit_timer;
    reg [2:0] bit_index;
    reg [7:0] data_shift;

`ifndef SYNTHESIS
    initial begin
        if (CLKS_PER_BIT < 8)
            $fatal(1, "uart_rx requires CLKS_PER_BIT >= 8");
    end
`endif

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            rx_meta <= 1'b1;
            rx_sync <= 1'b1;
        end else begin
            rx_meta <= rx;
            rx_sync <= rx_meta;
        end
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state            <= WAIT_IDLE;
            bit_timer        <= '0;
            bit_index        <= 3'd0;
            data_shift       <= 8'd0;
            rx_data          <= 8'd0;
            rx_done          <= 1'b0;
            rx_framing_error <= 1'b0;
        end else begin
            rx_done          <= 1'b0;
            rx_framing_error <= 1'b0;
            case (state)
                WAIT_IDLE: begin
                    // After reset/error, require a whole idle bit before rearming.
                    // A continuous break produces no repeated phantom frames.
                    if (!rx_sync) begin
                        bit_timer <= '0;
                    end else if (bit_timer == BIT_LAST) begin
                        bit_timer <= '0;
                        state     <= IDLE;
                    end else begin
                        bit_timer <= bit_timer + 1'b1;
                    end
                end
                IDLE: begin
                    if (!rx_sync) begin
                        bit_timer <= HALF_LAST;
                        state     <= START;
                    end
                end
                START: begin
                    if (bit_timer != 0) begin
                        bit_timer <= bit_timer - 1'b1;
                    end else if (rx_sync) begin
                        // The low pulse did not survive until the start midpoint.
                        state <= IDLE;
                    end else begin
                        bit_timer <= BIT_LAST;
                        bit_index <= 3'd0;
                        state     <= DATA;
                    end
                end
                DATA: begin
                    if (bit_timer != 0) begin
                        bit_timer <= bit_timer - 1'b1;
                    end else begin
                        // LSB first: after eight shifts, each bit is in place.
                        data_shift <= {rx_sync, data_shift[7:1]};
                        bit_timer <= BIT_LAST;
                        if (bit_index == 3'd7)
                            state <= STOP;
                        else
                            bit_index <= bit_index + 1'b1;
                    end
                end
                STOP: begin
                    if (bit_timer != 0) begin
                        bit_timer <= bit_timer - 1'b1;
                    end else if (rx_sync) begin
                        rx_data <= data_shift;
                        rx_done <= 1'b1;
                        state   <= IDLE;
                    end else begin
                        rx_framing_error <= 1'b1;
                        bit_timer <= '0;
                        state <= WAIT_IDLE;
                    end
                end
                default: begin
                    bit_timer <= '0;
                    state <= WAIT_IDLE;
                end
            endcase
        end
    end
endmodule

`default_nettype wire
