#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
mkdir -p build
check_mode="${1:-all}"
rtl=(rtl/common/reset_sync.sv rtl/uart/uart_tx.sv rtl/uart/uart_rx.sv rtl/uart/uart_top.sv)
bridge_rtl=(rtl/common/sync_fifo.sv rtl/bridge/uart_bridge.sv fpga/de10_lite/de10_lite_uart_top.sv)
aes_rtl=(rtl/aes/aes_sbox.sv rtl/aes/aes_sub_shift.sv rtl/aes/aes_mix_columns.sv rtl/aes/aes128_next_key.sv rtl/aes/aes128_core.sv)
ctr_rtl=(rtl/ctr/aes128_ctr_mask.sv rtl/ctr/aes128_ctr_stream.sv)
integration_rtl=(rtl/common/sync_fifo.sv rtl/bridge/uart_ctr_bridge.sv)
de10_ctr_common=(rtl/common/reset_sync.sv rtl/common/sync_fifo.sv rtl/uart/uart_rx.sv rtl/uart/uart_tx.sv rtl/bridge/uart_ctr_bridge.sv fpga/de10_lite/common/de10_lite_context_pkg.sv fpga/de10_lite/common/de10_lite_uart_ctr_top.sv)
de10_baseline_rtl=("${de10_ctr_common[@]}" "${aes_rtl[@]}" "${ctr_rtl[@]}" fpga/de10_lite/baseline/de10_lite_uart_baseline_top.sv)
de10_secure_rtl=("${de10_ctr_common[@]}" "${aes_rtl[@]}" "${ctr_rtl[@]}" fpga/de10_lite/secure/de10_lite_uart_secure_top.sv)
scope_rtl=(rtl/uart/uart_scope.sv fpga/de10_lite/uart_scope/de10_lite_uart_scope_top.sv)

run_test() {
    local test_name="$1"
    local test_label="$2"
    shift 2
    local test_sources=()
    local simulator_args=()
    case "$test_name" in
        uart_scope_tb) test_sources=("${rtl[@]}" "${scope_rtl[@]}") ;;
        uart_rx_tb|uart_tx_tb|uart_top_tb|uart_v1_regression_tb) test_sources=("${rtl[@]}") ;;
        sync_fifo_tb|uart_bridge_tb) test_sources=("${rtl[@]}" "${bridge_rtl[@]}") ;;
        aes_components_tb|aes128_core_tb) test_sources=("${aes_rtl[@]}") ;;
        aes128_ctr_mask_tb|aes128_ctr_stream_tb) test_sources=("${aes_rtl[@]}" "${ctr_rtl[@]}") ;;
        uart_ctr_bridge_tb) test_sources=("${rtl[@]}" "${aes_rtl[@]}" "${ctr_rtl[@]}" "${integration_rtl[@]}") ;;
        de10_lite_uart_ctr_top_tb) test_sources=("${de10_ctr_common[@]}" "${aes_rtl[@]}" "${ctr_rtl[@]}") ;;
        *) echo "Missing source list for test: $test_name" >&2; exit 2 ;;
    esac
    if [[ "$check_mode" == uart-waves ]]; then simulator_args=(+vcd); fi
    iverilog -g2012 -Wall -s "$test_name" "$@" \
        -o "build/$test_label.vvp" "${test_sources[@]}" "tb/$test_name.sv" 2>&1 | tee "build/$test_label.compile.log"
    vvp -n "build/$test_label.vvp" "${simulator_args[@]}" | tee "build/$test_label.log"
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
    run_test uart_scope_tb uart_scope_fast
    run_test uart_scope_tb uart_scope_50mhz_9600 -Puart_scope_tb.CLK_FREQ=50000000
}

lint_uart() {
    verilator --lint-only --Wall --top-module uart_top "${rtl[@]}" 2>&1 | tee build/lint.log
    verilator --lint-only --Wall --top-module de10_lite_uart_scope_top \
        "${rtl[@]}" "${scope_rtl[@]}" 2>&1 | tee build/uart-scope-lint.log
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
    yosys -q -Q -T -l build/uart-scope-synth.log -p \
        "read_verilog -sv ${rtl[*]} ${scope_rtl[*]}; hierarchy -check -top de10_lite_uart_scope_top; synth -top de10_lite_uart_scope_top; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/uart_scope.json"
    echo 'PASS UART scope structure: no check problems or inferred latches'
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

test_ctr() {
    run_test aes128_ctr_mask_tb aes128_ctr_mask
    run_test aes128_ctr_stream_tb aes128_ctr_stream
}

lint_ctr() {
    mkdir -p build/ctr
    verilator --lint-only --Wall --top-module aes128_ctr_stream \
        "${aes_rtl[@]}" "${ctr_rtl[@]}" 2>&1 | tee build/ctr/lint.log
}

synth_ctr() {
    mkdir -p build/ctr
    yosys -q -Q -T -l build/ctr/synth.log -p \
        "read_verilog -sv ${aes_rtl[*]} ${ctr_rtl[*]}; hierarchy -check -top aes128_ctr_stream; proc; opt; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/ctr/aes128_ctr_stream.json"
    echo 'PASS CTR structural elaboration: no check problems or inferred latches (not FPGA mapping)'
}

test_integration() {
    run_test uart_ctr_bridge_tb integration_secure_fast
    run_test uart_ctr_bridge_tb integration_baseline_fast -Puart_ctr_bridge_tb.ENABLE_AES=0
    run_test uart_ctr_bridge_tb integration_secure_50mhz -Puart_ctr_bridge_tb.CLK_FREQ=50000000 -Puart_ctr_bridge_tb.FIFO_DEPTH=1024
    run_test uart_ctr_bridge_tb integration_baseline_50mhz -Puart_ctr_bridge_tb.ENABLE_AES=0 -Puart_ctr_bridge_tb.CLK_FREQ=50000000 -Puart_ctr_bridge_tb.FIFO_DEPTH=1024
    run_test de10_lite_uart_ctr_top_tb de10_context_wrapper
}

test_integration_gps() {
    run_test uart_ctr_bridge_tb integration_secure_50mhz_gps \
        -Puart_ctr_bridge_tb.CLK_FREQ=50000000 -Puart_ctr_bridge_tb.FIFO_DEPTH=1024 \
        -Puart_ctr_bridge_tb.GPS_ONLY=1
    run_test uart_ctr_bridge_tb integration_baseline_50mhz_gps \
        -Puart_ctr_bridge_tb.ENABLE_AES=0 -Puart_ctr_bridge_tb.CLK_FREQ=50000000 \
        -Puart_ctr_bridge_tb.FIFO_DEPTH=1024 -Puart_ctr_bridge_tb.GPS_ONLY=1
}

lint_integration() {
    mkdir -p build/integration
    for variant in 0 1; do
        local lint_options=()
        if [[ "$variant" == 0 ]]; then
            # The baseline intentionally does not consume the CTR context.
            lint_options+=(--Wno-UNUSEDSIGNAL)
        fi
        verilator --lint-only --Wall "${lint_options[@]}" --top-module uart_ctr_bridge -GENABLE_AES="$variant" \
            "${rtl[@]}" "${aes_rtl[@]}" "${ctr_rtl[@]}" "${integration_rtl[@]}" \
            2>&1 | tee "build/integration/lint-$variant.log"
    done
    verilator --lint-only --Wall --Wno-UNUSEDSIGNAL --top-module de10_lite_uart_baseline_top \
        "${de10_baseline_rtl[@]}" 2>&1 | tee build/integration/lint-de10-baseline.log
    verilator --lint-only --Wall --top-module de10_lite_uart_secure_top \
        "${de10_secure_rtl[@]}" 2>&1 | tee build/integration/lint-de10-secure.log
}

synth_integration() {
    mkdir -p build/integration
    for variant in 0 1; do
        local baseline_assert=""
        if [[ "$variant" == 0 ]]; then
            baseline_assert='select -assert-none aes128*; select -clear;'
        fi
        yosys -q -Q -T -l "build/integration/synth-$variant.log" -p \
            "read_verilog -sv ${rtl[*]} ${aes_rtl[*]} ${ctr_rtl[*]} ${integration_rtl[*]}; chparam -set ENABLE_AES $variant uart_ctr_bridge; hierarchy -check -top uart_ctr_bridge; $baseline_assert proc; opt; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/integration/structure-$variant.json"
    done
    yosys -q -Q -T -l build/integration/synth-de10-baseline.log -p \
        "read_verilog -sv ${de10_baseline_rtl[*]}; hierarchy -check -top de10_lite_uart_baseline_top; proc; opt; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/integration/de10-baseline.json"
    yosys -q -Q -T -l build/integration/synth-de10-secure.log -p \
        "read_verilog -sv ${de10_secure_rtl[*]}; hierarchy -check -top de10_lite_uart_secure_top; proc; opt; check -assert; select -assert-none t:*latch* t:*LATCH*; select -clear; stat; write_json build/integration/de10-secure.json"
    echo 'PASS integration structure: no latches/check problems; no AES modules in baseline'
}

case "$check_mode" in
    uart) test_uart; lint_uart; synth_uart ;;
    uart-waves)
        run_test uart_top_tb uart_top_waves -Puart_top_tb.CLK_FREQ=50000000 -Puart_top_tb.NUM_BYTES=4
        run_test uart_scope_tb uart_scope_waves -Puart_scope_tb.CLK_FREQ=50000000
        echo 'PASS UART waveforms: build/uart_top.vcd and build/uart_scope.vcd (public signals)'
        ;;
    test) test_uart; test_bridge; test_aes; test_ctr; test_integration ;;
    lint) mkdir -p build/aes; lint_uart; lint_bridge; lint_aes; lint_ctr; lint_integration ;;
    bridge) test_bridge; lint_bridge ;;
    aes) test_aes; lint_aes; synth_aes ;;
    ctr) test_ctr; lint_ctr; synth_ctr ;;
    integration) test_integration; lint_integration; synth_integration ;;
    integration-gps) test_integration_gps ;;
    synth) synth_uart; synth_aes; synth_ctr; synth_integration ;;
    reference) test_reference ;;
    all)
        { date -u '+%Y-%m-%dT%H:%M:%SZ'; iverilog -V; verilator --version; yosys -V; } >build/tool_versions.txt 2>&1
        test_reference
        test_uart
        test_bridge
        test_aes
        test_ctr
        test_integration
        lint_uart
        lint_bridge
        lint_aes
        lint_ctr
        lint_integration
        synth_uart
        synth_aes
        synth_ctr
        synth_integration
        echo 'PASS: all UART, bridge, AES, CTR and integration HDL checks (PC verification follows)'
        ;;
    *) echo "Unknown check mode: $check_mode" >&2; exit 2 ;;
esac
