module baud_gen #(
    parameter CLK_FREQ  = 100000000,
    parameter BAUD_RATE = 9600
)(
    input  wire clk,
    input  wire rst,
    output wire baud_tick
);

    localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

    reg [31:0] counter;

    assign baud_tick = (counter == CLKS_PER_BIT - 1);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            counter <= 32'd0;
        end else begin
            if (baud_tick) begin
                counter <= 32'd0;
            end else begin
                counter <= counter + 1'b1;
            end
        end
    end

endmodule
