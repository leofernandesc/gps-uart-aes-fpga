#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
quartus_shell="${QUARTUS_SH:-}"
if [[ -z "$quartus_shell" ]]; then
    quartus_shell="$(command -v quartus_sh || true)"
    if [[ -z "$quartus_shell" ]]; then
        quartus_shell=/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_sh
    fi
fi
if [[ ! -x "$quartus_shell" ]]; then
    echo 'Set QUARTUS_SH to the installed quartus_sh executable.' >&2
    exit 1
fi
quartus_bin="$(dirname -- "$quartus_shell")"
mkdir -p "$project_dir/build/quartus_aes"
cd "$project_dir/fpga/aes_analysis"
trap 'aes_rc=$?; if (( aes_rc != 0 )); then printf "FAIL: AES analysis exited with code %s; inspect map/fit/timing logs\n" "$aes_rc" >../../build/quartus_aes/build-status.txt; fi' EXIT
printf 'RUNNING: AES analysis (virtual ports, no programming image)\n' >../../build/quartus_aes/build-status.txt
"$quartus_shell" --version >../../build/quartus_aes/tool-version.txt
"$quartus_bin/quartus_map" --read_settings_files=on --write_settings_files=off aes128_analysis 2>&1 | tee ../../build/quartus_aes/map.log
"$quartus_bin/quartus_fit" --read_settings_files=on --write_settings_files=off aes128_analysis 2>&1 | tee ../../build/quartus_aes/fit.log
"$quartus_bin/quartus_sta" -t ../../scripts/quartus_aes_timing.tcl 2>&1 | tee ../../build/quartus_aes/timing-audit.log
echo 'PASS: AES-only mapping, fit and INTERNAL timing audit; virtual boundaries excluded; no SOF' | tee ../../build/quartus_aes/build-status.txt
