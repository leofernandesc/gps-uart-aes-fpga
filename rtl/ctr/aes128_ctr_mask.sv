`timescale 1ns/1ps
`default_nettype none

// Counter blocks are {nonce[95:0], counter[31:0]}, MSB first.
// One held mask, with its slot reserved before starting the iterative AES.
// abort_req is synchronous and cancels this context; an AES operation already
// running is drained and discarded before another configuration is accepted.
module aes128_ctr_mask (
    input  wire         clk,
    input  wire         rst,
    input  wire         abort_req,
    input  wire         cfg_valid,
    output wire         cfg_ready,
    input  wire [127:0] cfg_key,
    input  wire [95:0]  cfg_nonce,
    input  wire [31:0]  cfg_counter,
    output wire         cfg_done,
    output reg          active,
    output wire         exhausted,
    output reg  [127:0] mask_data,
    output wire         mask_valid,
    input  wire         mask_ready,
    output reg          mask_last
);
    reg [95:0] nonce;
    reg [31:0] next_counter;
    reg result_valid, inflight, pending_last, last_issued;
    wire aes_key_ready, aes_key_done, aes_block_ready, aes_done;
    wire unused_key_valid, unused_busy;
    wire [127:0] aes_result;
    wire cfg_accept = cfg_valid && cfg_ready;
    wire issue = active && !rst && !abort_req && !inflight && !last_issued &&
                 (!result_valid || mask_ready) && aes_block_ready;

    assign cfg_ready = !rst && !abort_req && !active && aes_key_ready;
    assign cfg_done = active && !rst && !abort_req && aes_key_done;
    assign mask_valid = result_valid && active && !rst && !abort_req;
    assign exhausted = active && !rst && !abort_req && last_issued &&
                       !inflight && !result_valid;

    aes128_core aes_inst (
        .clk(clk), .rst(rst), .key_load(cfg_accept), .key_in(cfg_key),
        .key_ready(aes_key_ready), .key_valid(unused_key_valid),
        .key_done(aes_key_done), .start(issue), .block_in({nonce, next_counter}),
        .block_ready(aes_block_ready), .busy(unused_busy), .done(aes_done),
        .ciphertext(aes_result)
    );

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            active       <= 1'b0;
            nonce        <= 96'd0;
            next_counter <= 32'd0;
            result_valid <= 1'b0;
            inflight     <= 1'b0;
            pending_last <= 1'b0;
            last_issued  <= 1'b0;
            mask_data    <= 128'd0;
            mask_last    <= 1'b0;
        end else if (abort_req) begin
            active       <= 1'b0;
            nonce        <= 96'd0;
            next_counter <= 32'd0;
            result_valid <= 1'b0;
            inflight     <= 1'b0;
            pending_last <= 1'b0;
            last_issued  <= 1'b0;
            mask_data    <= 128'd0;
            mask_last    <= 1'b0;
        end else if (cfg_accept) begin
            active       <= 1'b1;
            nonce        <= cfg_nonce;
            next_counter <= cfg_counter;
            result_valid <= 1'b0;
            inflight     <= 1'b0;
            pending_last <= 1'b0;
            last_issued  <= 1'b0;
            mask_data    <= 128'd0;
            mask_last    <= 1'b0;
        end else if (active) begin
            if (mask_valid && mask_ready) begin
                result_valid <= 1'b0;
                mask_data <= 128'd0;
                mask_last <= 1'b0;
            end
            if (issue) begin
                inflight <= 1'b1;
                pending_last <= (next_counter == 32'hffffffff);
                // Saturate: never increment into the nonce or wrap to zero.
                if (next_counter == 32'hffffffff) last_issued <= 1'b1;
                else next_counter <= next_counter + 1'b1;
            end
            if (aes_done && inflight) begin
                mask_data <= aes_result;
                mask_last <= pending_last;
                result_valid <= 1'b1;
                inflight <= 1'b0;
            end
        end
    end
endmodule

`default_nettype wire
