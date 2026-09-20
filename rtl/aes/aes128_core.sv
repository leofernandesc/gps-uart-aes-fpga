`timescale 1ns/1ps
`default_nettype none

// Forward AES-128 primitive, with on-the-fly round-key expansion.
// Stores the master key and current round key, not an eleven-key register bank.
// Key preparation: 1 cycle. Block latency: 20 cycles (two phases per round).
// key_load && key_ready accepts a key. start && block_ready accepts a block.
// Key load wins if both requests occur while idle. Busy requests are not queued.
// rst asserts asynchronously; the caller must synchronize its deassertion.
module aes128_core (
    input  wire         clk,
    input  wire         rst,
    input  wire         key_load,
    input  wire [127:0] key_in,
    output wire         key_ready,
    output reg          key_valid,
    output reg          key_done,
    input  wire         start,
    input  wire [127:0] block_in,
    output wire         block_ready,
    output wire         busy,
    output reg          done,
    output reg  [127:0] ciphertext
);
    localparam [1:0] IDLE = 2'd0, KEY_READY = 2'd1, SUB_SHIFT = 2'd2, MIX_ADD = 2'd3;
    reg [1:0] state;
    reg [3:0] round_index;
    reg [127:0] master_key;
    reg [127:0] schedule_work, block_state;
    reg [7:0] rcon;
    wire [127:0] expanded_key, sub_shift_result, mix_result;

    assign busy = (state != IDLE);
    assign key_ready = !rst && !busy;
    assign block_ready = !rst && !busy && key_valid && !key_load;

    aes128_next_key expand_inst (.current_key(schedule_work), .rcon(rcon), .next_key(expanded_key));
    aes_sub_shift sub_inst (.state_in(block_state), .state_out(sub_shift_result));
    aes_mix_columns mix_inst (.state_in(block_state), .state_out(mix_result));

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state         <= IDLE;
            round_index   <= 4'd0;
            master_key    <= 128'd0;
            schedule_work <= 128'd0;
            block_state   <= 128'd0;
            rcon          <= 8'd0;
            key_valid     <= 1'b0;
            key_done      <= 1'b0;
            done          <= 1'b0;
            ciphertext    <= 128'd0;
        end else begin
            key_done <= 1'b0;
            done <= 1'b0;
            case (state)
                IDLE: begin
                    if (key_load) begin
                        master_key    <= key_in;
                        schedule_work <= 128'd0;
                        round_index   <= 4'd0;
                        rcon          <= 8'd0;
                        key_valid     <= 1'b0;
                        ciphertext    <= 128'd0;
                        block_state   <= 128'd0;
                        state         <= KEY_READY;
                    end else if (start && key_valid) begin
                        block_state <= block_in ^ master_key;
                        schedule_work <= master_key;
                        round_index <= 4'd1;
                        rcon        <= 8'h01;
                        state       <= SUB_SHIFT;
                    end
                end
                KEY_READY: begin
                    key_valid <= 1'b1;
                    key_done  <= 1'b1;
                    state     <= IDLE;
                end
                SUB_SHIFT: begin
                    block_state <= sub_shift_result;
                    // The next round key is computed in parallel with the
                    // data S-box/ShiftRows phase, ready for the following XOR.
                    schedule_work <= expanded_key;
                    rcon <= {rcon[6:0], 1'b0} ^ (rcon[7] ? 8'h1b : 8'h00);
                    state       <= MIX_ADD;
                end
                MIX_ADD: begin
                    if (round_index == 4'd10) begin
                        // Final round deliberately omits MixColumns.
                        ciphertext  <= block_state ^ schedule_work;
                        block_state <= 128'd0;
                        schedule_work <= 128'd0;
                        done        <= 1'b1;
                        state       <= IDLE;
                    end else begin
                        block_state <= mix_result ^ schedule_work;
                        round_index <= round_index + 1'b1;
                        state       <= SUB_SHIFT;
                    end
                end
                default: begin
                    state       <= IDLE;
                    key_valid   <= 1'b0;
                    master_key  <= 128'd0;
                    schedule_work <= 128'd0;
                    block_state <= 128'd0;
                    ciphertext  <= 128'd0;
                end
            endcase
        end
    end
endmodule

`default_nettype wire
