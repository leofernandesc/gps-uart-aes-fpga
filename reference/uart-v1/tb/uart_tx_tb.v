`timescale 1ns/1ps

module uart_tx_tb;

    reg clk;
    reg rst;
    reg baud_tick;
    reg tx_start;
    reg [7:0] tx_data;

    wire tx;
    wire tx_busy;
    wire tx_done;

    integer i;
    integer errors;

    uart_tx dut (
        .clk(clk),
        .rst(rst),
        .baud_tick(baud_tick),
        .tx_start(tx_start),
        .tx_data(tx_data),
        .tx(tx),
        .tx_busy(tx_busy),
        .tx_done(tx_done)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    task pulse_baud_tick;
        begin
            @(negedge clk);
            baud_tick = 1'b1;

            @(negedge clk);
            baud_tick = 1'b0;
        end
    endtask

    task send_and_check;
        input [7:0] expected_data;
        begin
            tx_data = expected_data;

            @(negedge clk);
            tx_start = 1'b1;

            @(negedge clk);
            tx_start = 1'b0;

            #1;

            if (tx !== 1'b0) begin
                $display("ERRO: start bit incorreto. tx=%b", tx);
                errors = errors + 1;
            end else begin
                $display("OK: start bit = 0");
            end

            for (i = 0; i < 8; i = i + 1) begin
                pulse_baud_tick();
                #1;

                if (tx !== expected_data[i]) begin
                    $display("ERRO: bit %0d incorreto. Esperado=%b, tx=%b",
                             i, expected_data[i], tx);
                    errors = errors + 1;
                end else begin
                    $display("OK: bit %0d = %b", i, tx);
                end
            end

            pulse_baud_tick();
            #1;

            if (tx !== 1'b1) begin
                $display("ERRO: stop bit incorreto. tx=%b", tx);
                errors = errors + 1;
            end else begin
                $display("OK: stop bit = 1");
            end

            pulse_baud_tick();

            @(posedge clk);
            #1;

            if (tx_done !== 1'b1) begin
                $display("ERRO: tx_done nao foi ativado.");
                errors = errors + 1;
            end else begin
                $display("OK: tx_done ativado.");
            end

            @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("sim/uart_tx_tb.vcd");
        $dumpvars(0, uart_tx_tb);

        rst        = 1'b1;
        baud_tick  = 1'b0;
        tx_start   = 1'b0;
        tx_data    = 8'd0;
        errors     = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst = 1'b0;

        repeat (2) @(posedge clk);

        $display("Testando envio de 8'hA5...");
        send_and_check(8'hA5);

        repeat (3) @(posedge clk);

        $display("Testando envio de 8'h3C...");
        send_and_check(8'h3C);

        repeat (5) @(posedge clk);

        if (errors == 0) begin
            $display("TESTE FINALIZADO COM SUCESSO.");
        end else begin
            $display("TESTE FINALIZADO COM %0d ERRO(S).", errors);
        end

        $finish;
    end

endmodule
