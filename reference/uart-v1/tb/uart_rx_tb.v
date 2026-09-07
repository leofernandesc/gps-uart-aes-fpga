`timescale 1ns/1ps

module uart_rx_tb;

    reg clk;
    reg rst;
    reg baud_tick;
    reg rx;

    wire [7:0] rx_data;
    wire       rx_done;

    integer i;
    integer errors;

    uart_rx dut (
        .clk(clk),
        .rst(rst),
        .baud_tick(baud_tick),
        .rx(rx),
        .rx_data(rx_data),
        .rx_done(rx_done)
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

    task send_serial_and_check;
        input [7:0] expected_data;
        begin
            rx = 1'b1;
            repeat (2) @(posedge clk);

            @(negedge clk);
            rx = 1'b0;

            @(posedge clk);
            #1;

            pulse_baud_tick();

            for (i = 0; i < 8; i = i + 1) begin
                @(negedge clk);
                rx = expected_data[i];

                pulse_baud_tick();
            end

            @(negedge clk);
            rx = 1'b1;

            pulse_baud_tick();

            @(posedge clk);
            #1;

            if (rx_done !== 1'b1) begin
                $display("ERRO: rx_done nao foi ativado.");
                errors = errors + 1;
            end else begin
                $display("OK: rx_done ativado.");
            end

            if (rx_data !== expected_data) begin
                $display("ERRO: rx_data incorreto. Esperado=%h, Recebido=%h",
                         expected_data, rx_data);
                errors = errors + 1;
            end else begin
                $display("OK: rx_data = %h", rx_data);
            end

            @(posedge clk);
            #1;

            rx = 1'b1;
        end
    endtask

    initial begin
        $dumpfile("sim/uart_rx_tb.vcd");
        $dumpvars(0, uart_rx_tb);

        rst       = 1'b1;
        baud_tick = 1'b0;
        rx        = 1'b1;
        errors    = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst = 1'b0;

        repeat (2) @(posedge clk);

        $display("Testando recepcao de 8'hA5...");
        send_serial_and_check(8'hA5);

        repeat (3) @(posedge clk);

        $display("Testando recepcao de 8'h3C...");
        send_serial_and_check(8'h3C);

        repeat (3) @(posedge clk);

        $display("Testando recepcao de 8'h00...");
        send_serial_and_check(8'h00);

        repeat (3) @(posedge clk);

        $display("Testando recepcao de 8'hFF...");
        send_serial_and_check(8'hFF);

        repeat (5) @(posedge clk);

        if (errors == 0) begin
            $display("TESTE FINALIZADO COM SUCESSO.");
        end else begin
            $display("TESTE FINALIZADO COM %0d ERRO(S).", errors);
        end

        $finish;
    end

endmodule
