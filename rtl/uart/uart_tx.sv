`timescale 1ns/1ps
`default_nettype none

// 8N1, LSB first. A request is accepted only when !tx_busy && !rst.
// CLKS_PER_BIT is an elaboration constant, not a runtime baud selector.
module uart_tx #(
    parameter integer CLKS_PER_BIT = 5208
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output reg        tx,
    output reg        tx_busy,
    output reg        tx_done
);
    localparam integer COUNT_WIDTH = (CLKS_PER_BIT > 1) ? $clog2(CLKS_PER_BIT) : 1;
    localparam [COUNT_WIDTH-1:0] BIT_LAST = COUNT_WIDTH'(CLKS_PER_BIT - 1);

    reg [COUNT_WIDTH-1:0] bit_timer;
    // Start is driven directly; this register holds eight data bits and stop.
    reg [8:0] frame;
    reg [3:0] bit_index;

`ifndef SYNTHESIS
    initial begin
        if (CLKS_PER_BIT < 8)
            $fatal(1, "uart_tx requires CLKS_PER_BIT >= 8");
    end
`endif

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            bit_timer <= '0;
            frame     <= 9'h1ff;
            bit_index <= 4'd0;
            tx        <= 1'b1;
            tx_busy   <= 1'b0;
            tx_done   <= 1'b0;
        end else begin
            tx_done <= 1'b0;
            if (!tx_busy) begin
                tx <= 1'b1;
                if (tx_start) begin
                    frame     <= {1'b1, tx_data};
                    bit_timer <= BIT_LAST;
                    bit_index <= 4'd0;
                    tx        <= 1'b0;
                    tx_busy   <= 1'b1;
                end
            end else if (bit_timer != 0) begin
                bit_timer <= bit_timer - 1'b1;
            end else if (bit_index == 4'd9) begin
                // The complete stop bit has elapsed, not merely its midpoint.
                tx      <= 1'b1;
                tx_busy <= 1'b0;
                tx_done <= 1'b1;
            end else begin
                frame     <= {1'b1, frame[8:1]};
                tx        <= frame[0];
                bit_index <= bit_index + 1'b1;
                bit_timer <= BIT_LAST;
            end
        end
    end
endmodule

`default_nettype wire
