#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
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
mkdir -p "$project_dir/build/quartus"
cd "$project_dir/fpga/de10_lite"
printf 'RUNNING: Quartus build (no board programming)\n' >../../build/quartus/build-status.txt
"$quartus_shell" --version >../../build/quartus/tool-version.txt
"$quartus_shell" --flow compile uart_bridge 2>&1 | tee ../../build/quartus/compile.log
"$quartus_sta" -t ../../scripts/quartus_timing.tcl 2>&1 | tee ../../build/quartus/timing-audit.log
test -s ../../build/quartus/uart_bridge.sof
echo 'PASS: Quartus compilation and timing audit; SOF generated, not programmed' | tee ../../build/quartus/build-status.txt
