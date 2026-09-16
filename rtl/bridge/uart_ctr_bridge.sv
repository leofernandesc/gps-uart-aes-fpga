`timescale 1ns/1ps
`default_nettype none

// Common datapath for baseline/secure builds. ENABLE_AES removes the cipher at
// elaboration, not with a runtime mux. Configuration uses the existing CTR
// handshake; this module does not parse serial commands or GPS sentences.
module uart_ctr_bridge #(
    parameter integer ENABLE_AES = 1,
    parameter integer CLK_FREQ = 50000000,
    parameter integer BAUD_RATE = 9600,
    parameter integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE,
    parameter integer FIFO_DEPTH = 1024,
    parameter integer LEVEL_WIDTH = $clog2(FIFO_DEPTH + 1)
) (
    input  wire clk,
    input  wire rst,
    input  wire rx,
    output wire tx,
    input  wire tx_enable,
    input  wire abort_req,
    input  wire cfg_valid,
    output wire cfg_ready,
    input  wire [127:0] cfg_key,
    input  wire [95:0] cfg_nonce,
    input  wire [31:0] cfg_counter,
    output wire cfg_done,
    output reg  active,
    output wire exhausted,
    output wire tx_busy,
    output wire rx_event,
    output wire tx_event,
    output reg  overflow_sticky,
    output reg  framing_sticky,
    output wire [LEVEL_WIDTH-1:0] fifo_level,
    output reg  [LEVEL_WIDTH-1:0] fifo_high_water
);
    wire [7:0] rx_data, fifo_data, output_data;
    wire rx_done, framing_error, fifo_valid, fifo_empty, fifo_full;
    wire unused_fifo_overflow;
    wire [LEVEL_WIDTH-1:0] raw_high_water;
    reg [7:0] held_data;
    reg held_valid, read_pending;
    wire cipher_ready, cipher_done, input_ready, output_valid;
    wire faulted = overflow_sticky || framing_sticky;
    wire cfg_accept = cfg_valid && cfg_ready;
    // active is clocked: asynchronous assertion, clock-aligned release. The
    // board wrapper must provide rst with synchronized deassertion.
    wire datapath_rst = rst || !active;
    wire read_request = active && !rst && !abort_req && !faulted &&
                        !held_valid && !read_pending && !fifo_empty;
    // Detect the same rejected write as sync_fifo, before consuming more data.
    wire overflow_now = active && rx_done && fifo_full && !read_request;
    wire framing_now = active && framing_error;
    wire fault_now = overflow_now || framing_now;
    wire cipher_abort = abort_req || fault_now;
    wire output_ready = active && !rst && !cipher_abort && !faulted &&
                        tx_enable && !tx_busy;
    wire tx_start = output_valid && output_ready;

    assign cfg_ready = !rst && !abort_req && !active && !faulted && cipher_ready;
    assign cfg_done = active && !cipher_abort && cipher_done;
    assign rx_event = active && !rst && !cipher_abort && rx_done;

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) rx_inst (
        .clk(clk), .rst(datapath_rst), .rx(rx), .rx_data(rx_data),
        .rx_done(rx_done), .rx_framing_error(framing_error)
    );
    sync_fifo #(.DEPTH(FIFO_DEPTH), .LEVEL_WIDTH(LEVEL_WIDTH)) fifo_inst (
        .clk(clk), .rst(datapath_rst), .wr_en(rx_done), .wr_data(rx_data),
        .rd_en(read_request), .rd_data(fifo_data), .rd_valid(fifo_valid),
        .empty(fifo_empty), .full(fifo_full), .level(fifo_level),
        .high_water(raw_high_water), .overflow(unused_fifo_overflow)
    );
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) tx_inst (
        .clk(clk), .rst(datapath_rst), .tx_start(tx_start),
        .tx_data(output_data), .tx(tx), .tx_busy(tx_busy), .tx_done(tx_event)
    );

    generate
        if (ENABLE_AES != 0) begin : secure
            wire unused_cipher_active;
            aes128_ctr_stream cipher_inst (
                .clk(clk), .rst(rst), .abort_req(cipher_abort),
                .cfg_valid(cfg_accept), .cfg_ready(cipher_ready),
                .cfg_key(cfg_key), .cfg_nonce(cfg_nonce), .cfg_counter(cfg_counter),
                .cfg_done(cipher_done), .active(unused_cipher_active),
                .exhausted(exhausted), .in_data(held_data),
                .in_valid(held_valid), .in_ready(input_ready),
                .out_data(output_data), .out_valid(output_valid),
                .out_ready(output_ready)
            );
        end else begin : baseline
            wire [255:0] unused_crypto_config = {cfg_key, cfg_nonce, cfg_counter};
            reg accepted;
            always @(posedge clk or posedge rst) begin
                if (rst) accepted <= 1'b0;
                else accepted <= cfg_accept;
            end
            assign cipher_ready = 1'b1;
            assign cipher_done = accepted;
            assign exhausted = 1'b0;
            assign input_ready = output_ready;
            assign output_valid = held_valid;
            assign output_data = held_data;
        end
    endgenerate

    // Reserve the one-byte holding register before requesting synchronous RAM.
    // rd_valid is only a pulse; held_valid survives any downstream stall.
    always @(posedge clk or posedge datapath_rst) begin
        if (datapath_rst) begin
            held_data <= 8'd0;
            held_valid <= 1'b0;
            read_pending <= 1'b0;
        end else begin
            if (read_request) read_pending <= 1'b1;
            if (fifo_valid) begin
                held_data <= fifo_data;
                held_valid <= 1'b1;
                read_pending <= 1'b0;
            end else if (held_valid && input_ready) begin
                held_valid <= 1'b0;
            end
        end
    end

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            active <= 1'b0;
            overflow_sticky <= 1'b0;
            framing_sticky <= 1'b0;
            fifo_high_water <= '0;
        end else begin
            if (active && raw_high_water > fifo_high_water)
                fifo_high_water <= raw_high_water;
            if (abort_req) begin
                active <= 1'b0;
                overflow_sticky <= 1'b0;
                framing_sticky <= 1'b0;
            end else if (fault_now) begin
                // A missing byte destroys CTR/reference alignment: stop the
                // capture and discard pending data, never silently continue.
                active <= 1'b0;
                overflow_sticky <= overflow_sticky || overflow_now;
                framing_sticky <= framing_sticky || framing_now;
            end else if (cfg_accept) begin
                active <= 1'b1;
                fifo_high_water <= '0;
            end
        end
    end
endmodule

`default_nettype wire
