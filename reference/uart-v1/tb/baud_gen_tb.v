`timescale 1ns/1ps

module baud_gen_tb;

    reg clk;
    reg rst;
    wire baud_tick;

    integer clk_cycle;
    integer last_tick_cycle;
    integer interval;
    integer measured_intervals;
    integer errors;

    localparam CLK_FREQ_TB  = 80;
    localparam BAUD_RATE_TB = 10;
    localparam EXPECTED_CLKS_PER_BIT = CLK_FREQ_TB / BAUD_RATE_TB;

    baud_gen #(
        .CLK_FREQ(CLK_FREQ_TB),
        .BAUD_RATE(BAUD_RATE_TB)
    ) dut (
        .clk(clk),
        .rst(rst),
        .baud_tick(baud_tick)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        $dumpfile("sim/baud_gen_tb.vcd");
        $dumpvars(0, baud_gen_tb);

        rst = 1'b1;

        clk_cycle          = 0;
        last_tick_cycle    = -1;
        interval           = 0;
        measured_intervals = 0;
        errors             = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst = 1'b0;

        $display("Iniciando teste do baud_gen...");
        $display("CLK_FREQ_TB = %0d", CLK_FREQ_TB);
        $display("BAUD_RATE_TB = %0d", BAUD_RATE_TB);
        $display("EXPECTED_CLKS_PER_BIT = %0d", EXPECTED_CLKS_PER_BIT);

        /*
            O primeiro baud_tick depois do reset serve apenas como referência.

            Como baud_tick é combinacional:
                baud_tick = 1 quando counter == CLKS_PER_BIT - 1

            Para CLKS_PER_BIT = 8:
                counter = 0 1 2 3 4 5 6 7
                                         ^
                                      baud_tick

            Por isso, em vez de validar o primeiro tick após o reset,
            este testbench mede o intervalo entre ticks consecutivos.
        */

        while (measured_intervals < 5) begin
            @(posedge clk);
            #1;

            clk_cycle = clk_cycle + 1;

            if (baud_tick == 1'b1) begin
                $display("INFO: baud_tick detectado no ciclo %0d, counter=%0d",
                         clk_cycle, dut.counter);

                if (last_tick_cycle == -1) begin
                    $display("INFO: primeiro baud_tick usado como referencia.");
                end else begin
                    interval = clk_cycle - last_tick_cycle;

                    if (interval == EXPECTED_CLKS_PER_BIT) begin
                        $display("OK: intervalo %0d = %0d ciclos.",
                                 measured_intervals + 1, interval);
                    end else begin
                        $display("ERRO: intervalo %0d = %0d ciclos. Esperado: %0d ciclos.",
                                 measured_intervals + 1, interval, EXPECTED_CLKS_PER_BIT);
                        errors = errors + 1;
                    end

                    measured_intervals = measured_intervals + 1;
                end

                last_tick_cycle = clk_cycle;
            end
        end

        if (errors == 0) begin
            $display("TESTE FINALIZADO COM SUCESSO.");
        end else begin
            $display("TESTE FINALIZADO COM %0d ERRO(S).", errors);
        end

        $finish;
    end

endmodule
