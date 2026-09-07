module uart_tx (
    input  wire       clk,
    input  wire       rst,
    input  wire       baud_tick,

    input  wire       tx_start,
    input  wire [7:0] tx_data,

    output reg        tx,
    output reg        tx_busy,
    output reg        tx_done
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

            tx        <= 1'b1;
            tx_busy   <= 1'b0;
            tx_done   <= 1'b0;
        end else begin
            tx_done <= 1'b0;

            case (state)

                IDLE: begin
                    tx        <= 1'b1;
                    tx_busy   <= 1'b0;
                    bit_index <= 3'd0;

                    if (tx_start) begin
                        data_reg <= tx_data;
                        tx       <= 1'b0;
                        tx_busy  <= 1'b1;
                        state    <= START_BIT;
                    end
                end

                START_BIT: begin
                    tx      <= 1'b0;
                    tx_busy <= 1'b1;

                    if (baud_tick) begin
                        tx        <= data_reg[0];
                        bit_index <= 3'd0;
                        state     <= DATA_BITS;
                    end
                end

                DATA_BITS: begin
                    tx      <= data_reg[bit_index];
                    tx_busy <= 1'b1;

                    if (baud_tick) begin
                        if (bit_index == 3'd7) begin
                            tx        <= 1'b1;
                            bit_index <= 3'd0;
                            state     <= STOP_BIT;
                        end else begin
                            bit_index <= bit_index + 1'b1;
                            tx        <= data_reg[bit_index + 1'b1];
                        end
                    end
                end

                STOP_BIT: begin
                    tx      <= 1'b1;
                    tx_busy <= 1'b1;

                    if (baud_tick) begin
                        state <= DONE;
                    end
                end

                DONE: begin
                    tx      <= 1'b1;
                    tx_busy <= 1'b0;
                    tx_done <= 1'b1;
                    state   <= IDLE;
                end

                default: begin
                    state     <= IDLE;
                    bit_index <= 3'd0;
                    data_reg  <= 8'd0;
                    tx        <= 1'b1;
                    tx_busy   <= 1'b0;
                    tx_done   <= 1'b0;
                end

            endcase
        end
    end

endmodule
