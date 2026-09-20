`timescale 1ns/1ps
`default_nettype none

// Common DE10-Lite wrapper for the two experimental builds.
//
// The baseline and secure projects instantiate this wrapper with different
// ENABLE_AES values.  The parameter is fixed during elaboration, so the
// baseline does not contain a runtime AES bypass or an AES datapath.
// Fixed context values are only for the first FPGA bring-up.  They are not a
// key-management protocol and must be replaced by the experiment controller
// before any real deployment.
module de10_lite_uart_ctr_top #(
    parameter integer ENABLE_AES = 1,
    parameter [127:0] CONTEXT_KEY =
        de10_lite_context_pkg::CONTEXT_KEY,
    parameter [95:0] CONTEXT_NONCE =
        de10_lite_context_pkg::CONTEXT_NONCE,
    parameter [31:0] CONTEXT_COUNTER =
        de10_lite_context_pkg::CONTEXT_COUNTER
) (
    input  wire       MAX10_CLK1_50,
    input  wire       KEY0_N,
    input  wire       UART_RX,
    output wire       UART_TX,
    output wire [9:0] LEDR
);
    wire rst;
    wire cfg_ready;
    wire cfg_done;
    wire active;
    wire exhausted;
    wire tx_busy;
    wire rx_event;
    wire tx_event;
    wire overflow_sticky;
    wire framing_sticky;
    wire [10:0] fifo_level;
    wire [10:0] fifo_high_water;

    reg cfg_pending;
    // This flag uses the FPGA power-up value to distinguish initial
    // provisioning from a later KEY0 reset.  Reprogramming the FPGA starts a
    // fresh context; pressing KEY0 after provisioning invalidates the static
    // context and leaves the bridge inactive until the next programming.
    reg context_booted = 1'b0;
    reg cfg_done_seen;
    reg rx_toggle;
    reg tx_toggle;
    reg [25:0] heartbeat_counter;

    reset_sync reset_inst (
        .clk  (MAX10_CLK1_50),
        .arst (!KEY0_N),
        .rst  (rst)
    );

    // Hold configuration valid until the bridge accepts it.  Only the first
    // reset after FPGA programming arms the static context.  A later KEY0
    // reset deliberately does not reload the same nonce/counter pair.
    always @(posedge MAX10_CLK1_50 or posedge rst) begin
        if (rst) begin
            cfg_pending <= !context_booted;
            if (!context_booted) context_booted <= 1'b1;
        end else if (cfg_pending && cfg_ready) begin
            cfg_pending <= 1'b0;
        end
    end

    always @(posedge MAX10_CLK1_50 or posedge rst) begin
        if (rst) begin
            cfg_done_seen    <= 1'b0;
            rx_toggle        <= 1'b0;
            tx_toggle        <= 1'b0;
            heartbeat_counter <= 26'd0;
        end else begin
            heartbeat_counter <= heartbeat_counter + 1'b1;
            if (cfg_done) cfg_done_seen <= 1'b1;
            if (rx_event) rx_toggle <= !rx_toggle;
            if (tx_event) tx_toggle <= !tx_toggle;
        end
    end

    uart_ctr_bridge #(
        .ENABLE_AES (ENABLE_AES),
        .CLK_FREQ  (50_000_000),
        .BAUD_RATE (9600),
        .FIFO_DEPTH (1024)
    ) bridge_inst (
        .clk              (MAX10_CLK1_50),
        .rst              (rst),
        .rx               (UART_RX),
        .tx               (UART_TX),
        .tx_enable        (1'b1),
        .abort_req        (1'b0),
        .cfg_valid        (cfg_pending),
        .cfg_ready        (cfg_ready),
        .cfg_key          (CONTEXT_KEY),
        .cfg_nonce        (CONTEXT_NONCE),
        .cfg_counter      (CONTEXT_COUNTER),
        .cfg_done         (cfg_done),
        .active           (active),
        .exhausted        (exhausted),
        .tx_busy          (tx_busy),
        .rx_event         (rx_event),
        .tx_event         (tx_event),
        .overflow_sticky  (overflow_sticky),
        .framing_sticky   (framing_sticky),
        .fifo_level       (fifo_level),
        .fifo_high_water  (fifo_high_water)
    );

    // LED meanings are identical in both builds:
    // 0 heartbeat, 1 configured/active, 2 RX event toggle, 3 TX event toggle,
    // 4 TX busy, 5 configuration completed, 6 FIFO overflow, 7 framing error,
    // 8 FIFO has data, 9 FIFO high-water mark or context exhaustion.
    assign LEDR[0] = heartbeat_counter[25];
    assign LEDR[1] = active;
    assign LEDR[2] = rx_toggle;
    assign LEDR[3] = tx_toggle;
    assign LEDR[4] = tx_busy;
    assign LEDR[5] = cfg_done_seen;
    assign LEDR[6] = overflow_sticky;
    assign LEDR[7] = framing_sticky;
    assign LEDR[8] = (fifo_level != 11'd0);
    assign LEDR[9] = (fifo_high_water >= 11'd512) || exhausted;

endmodule

`default_nettype wire
