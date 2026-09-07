`timescale 1ns/1ps
`default_nettype none

// Asynchronous assertion; deassertion after two rising edges of clk.
module reset_sync (
    input  wire clk,
    input  wire arst,
    output wire rst
);
    (* preserve *) reg [1:0] release_pipe;

    always @(posedge clk or posedge arst) begin
        if (arst)
            release_pipe <= 2'b11;
        else
            release_pipe <= {release_pipe[0], 1'b0};
    end

    assign rst = release_pipe[1];
endmodule

`default_nettype wire
