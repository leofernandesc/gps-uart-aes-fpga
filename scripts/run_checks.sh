#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
mkdir -p build
check_mode="${1:-all}"
rtl=(rtl/common/reset_sync.sv rtl/uart/uart_tx.sv rtl/uart/uart_rx.sv rtl/uart/uart_top.sv)
bridge_rtl=(rtl/common/sync_fifo.sv rtl/bridge/uart_bridge.sv fpga/de10_lite/de10_lite_uart_top.sv)
aes_rtl=(rtl/aes/aes_sbox.sv rtl/aes/aes_sub_shift.sv rtl/aes/aes_mix_columns.sv rtl/aes/aes128_next_key.sv rtl/aes/aes128_core.sv)

run_test() {
    local test_name="$1"
    local test_label="$2"
    shift 2
    iverilog -g2012 -Wall -s "$test_name" "$@" \
        -o "build/$test_label.vvp" "${rtl[@]}" "${bridge_rtl[@]}" "${aes_rtl[@]}" "tb/$test_name.sv" 2>&1 | tee "build/$test_label.compile.log"
    vvp -n "build/$test_label.vvp" | tee "build/$test_label.log"
}

test_uart() {
    run_test uart_rx_tb uart_rx_cpb32
    run_test uart_rx_tb uart_rx_cpb33 -Puart_rx_tb.CLKS_PER_BIT=33
    run_test uart_tx_tb uart_tx_cpb32
    run_test uart_tx_tb uart_tx_cpb33 -Puart_tx_tb.CLKS_PER_BIT=33
    run_test uart_top_tb uart_top_fast
    run_test uart_top_tb uart_top_50mhz_9600 -Puart_top_tb.CLK_FREQ=50000000 -Puart_top_tb.NUM_BYTES=16
    # Rename only a generated build copy; the historical source remains untouched.
    sed 's/\<uart_tx\>/uart_tx_v1/g' reference/uart-v1/rtl/uart_tx.v >build/uart_tx_v1.v
    # Only the legacy modules have no timescale declaration.
    run_test uart_v1_regression_tb uart_v1_regression -Wno-timescale build/uart_tx_v1.v reference/uart-v1/rtl/baud_gen.v
}

lint_uart() {
    verilator --lint-only --Wall --top-module uart_top "${rtl[@]}" 2>&1 | tee build/lint.log
}

test_bridge() {
    run_test sync_fifo_tb sync_fifo_depth2 -Psync_fifo_tb.DEPTH=2
    run_test sync_fifo_tb sync_fifo_depth8
    run_test sync_fifo_tb sync_fifo_depth1024 -Psync_fifo_tb.DEPTH=1024
    run_test uart_bridge_tb uart_bridge_fast
    run_test uart_bridge_tb uart_bridge_50mhz_9600 \
        -Puart_bridge_tb.CLK_FREQ=50000000 -Puart_bridge_tb.FIFO_DEPTH=1024 -Puart_bridge_tb.STRESS=0
}

lint_bridge() {
    verilator --lint-only --Wall --top-module de10_lite_uart_top \
        "${rtl[@]}" "${bridge_rtl[@]}" 2>&1 | tee build/bridge-lint.log
}

synth_uart() {
    # Structural check only: not Quartus mapping, timing, or FPGA resource data.
    yosys -q -Q -T -l build/synth.log -p \
        "read_verilog -sv ${rtl[*]}; hierarchy -check -top uart_top; synth -top uart_top; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/uart_top.json"
    echo 'PASS structural synthesis: no check problems or inferred latches (not FPGA mapping)'
}

test_aes() {
    (cd reference/aes-cavp && sha256sum -c SHA256SUMS)
    run_test aes_components_tb aes_components
    run_test aes128_core_tb aes128_core
}

lint_aes() {
    verilator --lint-only --Wall --top-module aes128_analysis_top \
        rtl/common/reset_sync.sv "${aes_rtl[@]}" fpga/aes_analysis/aes128_analysis_top.sv \
        2>&1 | tee build/aes/lint.log
}

synth_aes() {
    mkdir -p build/aes
    yosys -q -Q -T -l build/aes/synth.log -p \
        "read_verilog -sv ${aes_rtl[*]}; hierarchy -check -top aes128_core; proc; opt; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/aes/aes128_core.json"
    echo 'PASS AES structural elaboration: no check problems or inferred latches (not FPGA mapping)'
}

test_reference() {
    (cd reference/uart-v1 && sha256sum -c SHA256SUMS)
    local legacy_dir="$project_dir/reference/uart-v1"
    mkdir -p build/reference/sim
    for legacy_test in baud_gen_tb uart_rx_tb uart_tx_tb uart_tb; do
        iverilog -g2012 -s "$legacy_test" -o "build/reference/$legacy_test.vvp" \
            "$legacy_dir"/rtl/*.v "$legacy_dir/tb/$legacy_test.v"
        (cd build/reference && vvp -n "$legacy_test.vvp") | tee "build/reference/$legacy_test.log"
        # Historical benches print failures but do not return a nonzero exit code.
        if ! grep -q 'TESTE FINALIZADO COM SUCESSO' "build/reference/$legacy_test.log" || \
           grep -q 'ERRO:' "build/reference/$legacy_test.log"; then
            echo "ERROR: legacy test failed: $legacy_test" >&2
            exit 1
        fi
    done
}

case "$check_mode" in
    test) test_uart; test_bridge; test_aes ;;
    lint) mkdir -p build/aes; lint_uart; lint_bridge; lint_aes ;;
    bridge) test_bridge; lint_bridge ;;
    aes) test_aes; lint_aes; synth_aes ;;
    synth) synth_uart; synth_aes ;;
    reference) test_reference ;;
    all)
        printf 'RUNNING: UART, bridge and AES checks\n' >build/check-status.txt
        { date -u '+%Y-%m-%dT%H:%M:%SZ'; iverilog -V; verilator --version; yosys -V; } >build/tool_versions.txt 2>&1
        test_reference
        test_uart
        test_bridge
        test_aes
        lint_uart
        lint_bridge
        lint_aes
        synth_uart
        synth_aes
        echo 'PASS: all UART, bridge and AES checks' | tee build/check-status.txt
        ;;
    *) echo "Unknown check mode: $check_mode" >&2; exit 2 ;;
esac
