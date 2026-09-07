module uart_rx (
    input  wire       clk,
    input  wire       rst,
    input  wire       baud_tick,

    input  wire       rx,

    output reg  [7:0] rx_data,
    output reg        rx_done
);

    localparam IDLE      = 3'd0;
    localparam START_BIT = 3'd1;
    localparam DATA_BITS = 3'd2;
    localparam STOP_BIT  = 3'd3;
    localparam DONE      = 3'd4;

    reg [2:0] state;
    reg [2:0] bit_index;
    reg [7:0] data_reg;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state     <= IDLE;
            bit_index <= 3'd0;
            data_reg  <= 8'd0;
            rx_data   <= 8'd0;
            rx_done   <= 1'b0;
        end else begin
            rx_done <= 1'b0;

            case (state)

                IDLE: begin
                    bit_index <= 3'd0;

                    if (rx == 1'b0) begin
                        state <= START_BIT;
                    end
                end

                START_BIT: begin
                    if (baud_tick) begin
                        if (rx == 1'b0) begin
                            state <= DATA_BITS;
                        end else begin
                            state <= IDLE;
                        end
                    end
                end

                DATA_BITS: begin
                    if (baud_tick) begin
                        data_reg[bit_index] <= rx;

                        if (bit_index == 3'd7) begin
                            bit_index <= 3'd0;
                            state     <= STOP_BIT;
                        end else begin
                            bit_index <= bit_index + 1'b1;
                        end
                    end
                end

                STOP_BIT: begin
                    if (baud_tick) begin
                        if (rx == 1'b1) begin
                            rx_data <= data_reg;
                            state   <= DONE;
                        end else begin
                            state <= IDLE;
                        end
                    end
                end

                DONE: begin
                    rx_done <= 1'b1;
                    state   <= IDLE;
                end

                default: begin
                    state     <= IDLE;
                    bit_index <= 3'd0;
                    data_reg  <= 8'd0;
                    rx_data   <= 8'd0;
                    rx_done   <= 1'b0;
                end

            endcase
        end
    end

endmodule
