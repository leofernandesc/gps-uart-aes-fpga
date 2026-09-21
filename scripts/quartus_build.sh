#!/usr/bin/env bash
set -euo pipefail
umask 077
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
board="${1:-de10_lite}"
design="${2:-bridge}"
case "$board/$design" in
    de10_lite/bridge)
        quartus_project=uart_bridge
        target_dir="$project_dir/fpga/de10_lite"
        output_dir="$project_dir/build/quartus"
        ;;
    de10_lite/uart_scope)
        quartus_project=uart_scope
        target_dir="$project_dir/fpga/de10_lite/uart_scope"
        output_dir="$project_dir/build/de10_lite/uart_scope"
        ;;
    de10_lite/baseline)
        quartus_project=uart_baseline
        target_dir="$project_dir/fpga/de10_lite/baseline"
        output_dir="$project_dir/build/de10_lite/baseline"
        ;;
    de10_lite/secure)
        quartus_project=uart_secure
        target_dir="$project_dir/fpga/de10_lite/secure"
        output_dir="$project_dir/build/de10_lite/secure"
        ;;
    de10_nano/uart_scope)
        quartus_project=uart_scope
        target_dir="$project_dir/fpga/de10_nano/uart_scope"
        output_dir="$project_dir/build/de10_nano/uart_scope"
        ;;
    cyclone4/uart_scope)
        quartus_project=uart_scope
        target_dir="$project_dir/fpga/cyclone4/uart_scope"
        output_dir="$project_dir/build/cyclone4/uart_scope"
        ;;
    cyclone4/baseline)
        quartus_project=uart_baseline
        target_dir="$project_dir/fpga/cyclone4/baseline"
        output_dir="$project_dir/build/cyclone4/baseline"
        ;;
    cyclone4/secure)
        quartus_project=uart_secure
        target_dir="$project_dir/fpga/cyclone4/secure"
        output_dir="$project_dir/build/cyclone4/secure"
        ;;
    *)
        echo "Unavailable target: $board/$design. Available: de10_lite/{bridge,uart_scope,baseline,secure}, cyclone4/{uart_scope,baseline,secure}, de10_nano/uart_scope." >&2
        exit 2 ;;
esac
quartus_shell="${QUARTUS_SH:-}"
if [[ -z "$quartus_shell" ]]; then
    if command -v quartus_sh >/dev/null 2>&1; then
        quartus_shell="$(command -v quartus_sh)"
    else
        quartus_shell=/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_sh
    fi
fi
if [[ ! -x "$quartus_shell" ]]; then
    echo 'Quartus not found. Set QUARTUS_SH to the installed quartus_sh executable.' >&2
    exit 1
fi
quartus_sta="$(dirname -- "$quartus_shell")/quartus_sta"
mkdir -p "$output_dir"
record_build_exit() {
    local build_exit_code=$?
    if (( build_exit_code != 0 )); then
        printf 'FAIL: build exited with code %s; previous SOF may be stale\n' "$build_exit_code" >"$output_dir/build-status.txt"
    fi
}
trap record_build_exit EXIT
context_file="${CONTEXT_FILE:-}"
if [[ "$design" == baseline || "$design" == secure ]]; then
    context_output="$output_dir/context_params.sv"
    if [[ -n "$context_file" ]]; then
        if [[ "$context_file" != /* ]]; then
            context_file="$project_dir/$context_file"
        fi
        if [[ ! -f "$context_file" ]]; then
            echo "Context file not found: $context_file" >&2
            exit 1
        fi
        expected_mode=aes-128-ctr
        if [[ "$design" == baseline ]]; then
            expected_mode=baseline
        fi
        python3 "$project_dir/scripts/context.py" render-sv \
            --context "$context_file" \
            --output "$context_output" \
            --expected-mode "$expected_mode"
    else
        cp "$project_dir/fpga/de10_lite/common/de10_lite_context_pkg.sv" \
            "$context_output"
        chmod 600 "$context_output"
    fi
fi
cd "$target_dir"
printf 'RUNNING: Quartus %s/%s (no board programming)\n' "$board" "$design" >"$output_dir/build-status.txt"
"$quartus_shell" --version >"$output_dir/tool-version.txt"
if [[ "$design" == baseline || "$design" == secure ]]; then
    python3 "$project_dir/scripts/build_manifest.py" begin --output "$output_dir" \
        --qsf "$target_dir/$quartus_project.qsf" --board "$board" --design "$design"
fi
"$quartus_shell" --flow compile "$quartus_project" 2>&1 | tee "$output_dir/compile.log"
"$quartus_sta" -t "$project_dir/scripts/quartus_timing.tcl" "$quartus_project" "$output_dir" 2>&1 | tee "$output_dir/timing-audit.log"
test -s "$output_dir/$quartus_project.sof"
if [[ "$design" == baseline || "$design" == secure ]]; then
    python3 "$project_dir/scripts/build_manifest.py" finish --output "$output_dir"
fi
echo 'PASS: Quartus compilation and timing audit; SOF generated, not programmed' | tee "$output_dir/build-status.txt"
