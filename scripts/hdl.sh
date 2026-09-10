#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
check_mode="${1:-all}"
case "$check_mode" in all|test|lint|synth|reference|bridge|aes|ctr) ;; *)
    echo "Usage: bash scripts/hdl.sh {all|test|lint|synth|reference|bridge|aes|ctr}" >&2; exit 2;;
esac

hdl_runner="${HDL_RUNNER:-auto}"
case "$hdl_runner" in auto|native|docker) ;; *)
    echo "HDL_RUNNER must be auto, native, or docker" >&2; exit 2;;
esac
if [[ "$hdl_runner" == auto ]]; then
    hdl_runner=native
    for hdl_tool in iverilog vvp verilator yosys; do
        if ! command -v "$hdl_tool" >/dev/null 2>&1; then hdl_runner=docker; fi
    done
fi

mkdir -p "$project_dir/build"
if [[ "$check_mode" == all ]]; then
    printf 'RUNNING: HDL regression and independent PC verification\n' >"$project_dir/build/check-status.txt"
    record_check_exit() {
        local check_exit_code=$?
        if (( check_exit_code != 0 )); then
            printf 'FAIL: check exited with code %s\n' "$check_exit_code" >"$project_dir/build/check-status.txt"
        fi
    }
    trap record_check_exit EXIT
fi
case "$check_mode" in
    all|test|aes) python3 "$project_dir/scripts/aes_vectors.py" ;;
esac
case "$check_mode" in
    all|test|ctr) python3 "$project_dir/scripts/ctr_vectors.py" ;;
esac
if [[ "$hdl_runner" == native ]]; then
    bash "$project_dir/scripts/run_checks.sh" "$check_mode"
else
    # Already installed in this workspace. Do not pull/install tools silently.
    hdl_image="${HDL_DOCKER_IMAGE:-isaiassh/unic-cass-tools:1.0.7}"
    if ! docker image inspect "$hdl_image" >/dev/null; then
        echo "Docker unavailable or image missing: $hdl_image" >&2
        echo "Start Docker/allow access, or install HDL tools and set HDL_RUNNER=native." >&2
        exit 1
    fi
    docker run --rm --read-only --network none --tmpfs /tmp \
        --user "$(id -u):$(id -g)" \
        --mount "type=bind,source=$project_dir,target=/work,readonly" \
        --mount "type=bind,source=$project_dir/build,target=/work/build" \
        --workdir /work --entrypoint /bin/bash "$hdl_image" \
        -lc 'exec bash /work/scripts/run_checks.sh "$@"' bash "$check_mode"
fi
case "$check_mode" in
    all|test|ctr) python3 "$project_dir/scripts/ctr_vectors.py" --verify ;;
esac
if [[ "$check_mode" == all ]]; then
    echo 'PASS: UART, bridge, AES, CTR and independent PC verification' | tee "$project_dir/build/check-status.txt"
fi
