`timescale 1ns/1ps

module uart_tb;

    reg clk;
    reg rst;

    reg        tx_start;
    reg  [7:0] tx_data;

    wire tx;
    wire tx_busy;
    wire tx_done;

    wire [7:0] rx_data;
    wire       rx_done;

    integer errors;

    localparam CLK_FREQ_TB  = 320;
    localparam BAUD_RATE_TB = 10;
    localparam CLKS_PER_BIT = CLK_FREQ_TB / BAUD_RATE_TB;

    uart_top #(
        .CLK_FREQ(CLK_FREQ_TB),
        .BAUD_RATE(BAUD_RATE_TB)
    ) dut (
        .clk(clk),
        .rst(rst),

        .tx_start(tx_start),
        .tx_data(tx_data),

        .tx(tx),
        .tx_busy(tx_busy),
        .tx_done(tx_done),

        .rx(tx),

        .rx_data(rx_data),
        .rx_done(rx_done)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    task send_and_check;
        input [7:0] data;
        integer timeout;
        begin
            tx_data = data;

            /*
                Alinha o início da transmissão próximo ao baud_tick.
                Isso facilita a análise no GTKWave e evita desalinhamento
                artificial no teste de loopback.
            */
            @(negedge clk);
            while (dut.baud_inst.counter != (CLKS_PER_BIT - 1)) begin
                @(negedge clk);
            end

            tx_start = 1'b1;

            @(negedge clk);
            tx_start = 1'b0;

            timeout = 0;

            while ((rx_done !== 1'b1) && (timeout < 2000)) begin
                @(posedge clk);
                #1;
                timeout = timeout + 1;
            end

            if (timeout >= 2000) begin
                $display("ERRO: timeout esperando rx_done para o byte %h", data);
                errors = errors + 1;
            end else begin
                if (rx_data !== data) begin
                    $display("ERRO: enviado=%h, recebido=%h", data, rx_data);
                    errors = errors + 1;
                end else begin
                    $display("OK: enviado=%h, recebido=%h", data, rx_data);
                end
            end

            repeat (5) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("sim/uart_tb.vcd");
        $dumpvars(0, uart_tb);

        rst      = 1'b1;
        tx_start = 1'b0;
        tx_data  = 8'd0;
        errors   = 0;

        repeat (5) @(posedge clk);
        @(negedge clk);
        rst = 1'b0;

        repeat (5) @(posedge clk);

        $display("Iniciando teste UART em loopback...");
        $display("CLK_FREQ_TB = %0d", CLK_FREQ_TB);
        $display("BAUD_RATE_TB = %0d", BAUD_RATE_TB);
        $display("CLKS_PER_BIT = %0d", CLKS_PER_BIT);

        send_and_check(8'h55);
        send_and_check(8'hA5);
        send_and_check(8'h00);
        send_and_check(8'hFF);
        send_and_check(8'h3C);

        repeat (10) @(posedge clk);

        if (errors == 0) begin
            $display("TESTE FINALIZADO COM SUCESSO.");
        end else begin
            $display("TESTE FINALIZADO COM %0d ERRO(S).", errors);
        end

        $finish;
    end

endmodule
