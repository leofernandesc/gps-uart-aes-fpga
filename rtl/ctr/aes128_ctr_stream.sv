`timescale 1ns/1ps
`default_nettype none

// Two mask reserves: current_mask here and the held result in mask_inst.
// A byte transfers at in_valid && in_ready == out_valid && out_ready.
// Upstream must hold in_valid/in_data while stalled. There is no payload
// storage here: the XOR is combinational, and a mask advances only on transfer.
module aes128_ctr_stream (
    input  wire         clk,
    input  wire         rst,
    input  wire         abort_req,
    input  wire         cfg_valid,
    output wire         cfg_ready,
    input  wire [127:0] cfg_key,
    input  wire [95:0]  cfg_nonce,
    input  wire [31:0]  cfg_counter,
    output wire         cfg_done,
    output wire         active,
    output wire         exhausted,
    input  wire [7:0]   in_data,
    input  wire         in_valid,
    output wire         in_ready,
    output wire [7:0]   out_data,
    output wire         out_valid,
    input  wire         out_ready
);
    reg [127:0] current_mask;
    reg [3:0] byte_index;
    reg current_valid;
    wire [127:0] next_mask;
    wire next_valid, next_ready, masks_exhausted, unused_mask_last;
    wire transfer = out_valid && out_ready;

    assign out_valid = active && current_valid && in_valid && !rst && !abort_req;
    assign in_ready = active && current_valid && out_ready && !rst && !abort_req;
    assign out_data = out_valid ? (in_data ^ current_mask[127:120]) : 8'd0;
    assign next_ready = !rst && !abort_req &&
                        (!current_valid || (transfer && byte_index == 4'd15));
    assign exhausted = masks_exhausted && !current_valid;

    aes128_ctr_mask mask_inst (
        .clk(clk), .rst(rst), .abort_req(abort_req),
        .cfg_valid(cfg_valid), .cfg_ready(cfg_ready), .cfg_key(cfg_key),
        .cfg_nonce(cfg_nonce), .cfg_counter(cfg_counter), .cfg_done(cfg_done),
        .active(active), .exhausted(masks_exhausted),
        .mask_data(next_mask), .mask_valid(next_valid), .mask_ready(next_ready),
        .mask_last(unused_mask_last)
    );

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_mask  <= 128'd0;
            current_valid <= 1'b0;
            byte_index    <= 4'd0;
        end else if (abort_req || (cfg_valid && cfg_ready)) begin
            current_mask  <= 128'd0;
            current_valid <= 1'b0;
            byte_index    <= 4'd0;
        end else if (next_valid && next_ready) begin
            current_mask  <= next_mask;
            current_valid <= 1'b1;
            byte_index    <= 4'd0;
        end else if (transfer) begin
            current_mask <= {current_mask[119:0], 8'd0};
            if (byte_index == 4'd15) begin
                current_valid <= 1'b0;
                byte_index <= 4'd0;
            end else byte_index <= byte_index + 1'b1;
        end
    end
endmodule

`default_nettype wire
