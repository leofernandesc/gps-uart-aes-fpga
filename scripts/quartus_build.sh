#!/usr/bin/env bash
set -euo pipefail
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
    cyclone4/*)
        echo 'Cyclone IV: confirm board, exact device, oscillator, clock pin and I/O levels before creating a hardware target. See fpga/cyclone4/README.md.' >&2
        exit 2 ;;
    *)
        echo "Unavailable target: $board/$design. Available: de10_lite/{bridge,uart_scope}. Integrated baseline/secure are pending." >&2
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
cd "$target_dir"
printf 'RUNNING: Quartus %s/%s (no board programming)\n' "$board" "$design" >"$output_dir/build-status.txt"
"$quartus_shell" --version >"$output_dir/tool-version.txt"
"$quartus_shell" --flow compile "$quartus_project" 2>&1 | tee "$output_dir/compile.log"
"$quartus_sta" -t "$project_dir/scripts/quartus_timing.tcl" "$quartus_project" "$output_dir" 2>&1 | tee "$output_dir/timing-audit.log"
test -s "$output_dir/$quartus_project.sof"
echo 'PASS: Quartus compilation and timing audit; SOF generated, not programmed' | tee "$output_dir/build-status.txt"
