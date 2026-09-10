`timescale 1ns/1ps
`default_nettype none

// Forward AES-128 primitive; CTR is a separate, future consumer of this core.
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
    localparam [1:0] IDLE = 2'd0, EXPAND = 2'd1, SUB_SHIFT = 2'd2, MIX_ADD = 2'd3;
    reg [1:0] state;
    reg [3:0] round_index;
    reg [127:0] round_keys [0:10];
    reg [127:0] schedule_work, block_state;
    reg [7:0] rcon;
    wire [127:0] expanded_key, sub_shift_result, mix_result;

    assign busy = (state != IDLE);
    assign key_ready = !rst && !busy;
    assign block_ready = !rst && !busy && key_valid && !key_load;

    aes128_next_key expand_inst (.current_key(schedule_work), .rcon(rcon), .next_key(expanded_key));
    aes_sub_shift sub_inst (.state_in(block_state), .state_out(sub_shift_result));
    aes_mix_columns mix_inst (.state_in(block_state), .state_out(mix_result));

    // Separate constant-index write enables avoid a procedural loop variable
    // being mistaken for state by synthesis. All key storage resets explicitly.
    genvar k;
    generate for (k = 0; k < 11; k = k + 1) begin : key_storage
        if (k == 0) begin : original_key
            always @(posedge clk or posedge rst) begin
                if (rst) round_keys[k] <= 128'd0;
                else if (state == IDLE && key_load) round_keys[k] <= key_in;
            end
        end else begin : derived_key
            always @(posedge clk or posedge rst) begin
                if (rst) round_keys[k] <= 128'd0;
                else if (state == EXPAND && round_index == 4'(k))
                    round_keys[k] <= expanded_key;
            end
        end
    end endgenerate

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state         <= IDLE;
            round_index   <= 4'd0;
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
                        schedule_work <= key_in;
                        round_index   <= 4'd1;
                        rcon          <= 8'h01;
                        key_valid     <= 1'b0;
                        ciphertext    <= 128'd0;
                        block_state   <= 128'd0;
                        state         <= EXPAND;
                    end else if (start && key_valid) begin
                        block_state <= block_in ^ round_keys[0];
                        round_index <= 4'd1;
                        state       <= SUB_SHIFT;
                    end
                end
                EXPAND: begin
                    schedule_work <= expanded_key;
                    rcon <= {rcon[6:0], 1'b0} ^ (rcon[7] ? 8'h1b : 8'h00);
                    if (round_index == 4'd10) begin
                        key_valid <= 1'b1;
                        key_done  <= 1'b1;
                        state     <= IDLE;
                    end else begin
                        round_index <= round_index + 1'b1;
                    end
                end
                SUB_SHIFT: begin
                    block_state <= sub_shift_result;
                    state       <= MIX_ADD;
                end
                MIX_ADD: begin
                    if (round_index == 4'd10) begin
                        // Final round deliberately omits MixColumns.
                        ciphertext  <= block_state ^ round_keys[10];
                        block_state <= 128'd0;
                        done        <= 1'b1;
                        state       <= IDLE;
                    end else begin
                        block_state <= mix_result ^ round_keys[round_index];
                        round_index <= round_index + 1'b1;
                        state       <= SUB_SHIFT;
                    end
                end
                default: begin
                    state       <= IDLE;
                    key_valid   <= 1'b0;
                    block_state <= 128'd0;
                    ciphertext  <= 128'd0;
                end
            endcase
        end
    end
endmodule

`default_nettype wire
