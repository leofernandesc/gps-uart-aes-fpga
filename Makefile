.PHONY: check test lint synth reference bridge aes ctr integration integration-gps pc context gps-replay gps-capture-check serial-bench manuscript-check metrics metrics-snapshot fpga baseline-fpga secure-fpga aes-fpga uart uart-waves uart-fpga de10-nano-uart-fpga

BOARD ?= de10_lite
DESIGN ?= bridge
METRICS_SNAPSHOT ?= docs/evidence/de10-lite-postfit-2026-09-30.json

# HDL_RUNNER=auto (default), native, or docker.
check:
	bash scripts/hdl.sh all

test:
	bash scripts/hdl.sh test

lint:
	bash scripts/hdl.sh lint

synth:
	bash scripts/hdl.sh synth

reference:
	bash scripts/hdl.sh reference

bridge:
	bash scripts/hdl.sh bridge

# Quartus build and timing analysis; does not connect to/program a board.
fpga:
	bash scripts/quartus_build.sh "$(BOARD)" "$(DESIGN)"

# Separate elaborations used by the experimental comparison on the DE10-Lite.
baseline-fpga:
	CONTEXT_FILE="$(CONTEXT_FILE)" bash scripts/quartus_build.sh de10_lite baseline

secure-fpga:
	CONTEXT_FILE="$(CONTEXT_FILE)" bash scripts/quartus_build.sh de10_lite secure

# UART RX/TX and autonomous bench only; no AES/FIFO simulation.
uart:
	bash scripts/hdl.sh uart

uart-waves:
	bash scripts/hdl.sh uart-waves

# Autonomous 0x55 transmitter + RX diagnostics, for oscilloscope/jumper tests.
uart-fpga:
	bash scripts/quartus_build.sh "$(BOARD)" uart_scope

de10-nano-uart-fpga:
	bash scripts/quartus_build.sh de10_nano uart_scope

aes:
	bash scripts/hdl.sh aes

ctr:
	bash scripts/hdl.sh ctr

integration:
	bash scripts/hdl.sh integration

# Full public NMEA replay at the production 50 MHz/38400 baud timing; slower
# than the regular regression and intentionally kept as a separate target.
integration-gps:
	bash scripts/hdl.sh integration-gps

pc:
	python3 -m unittest discover -s tb -p 'test_*.py' -v

context:
	python3 -m unittest discover -s tb -p 'test_context.py' -v

gps-replay:
	python3 scripts/gps_fixture.py

gps-capture-check:
	@if [ -z "$(GPS_CAPTURE)" ]; then echo "Uso: make gps-capture-check GPS_CAPTURE=arquivo.bin" >&2; exit 2; fi
	python3 scripts/gps_capture.py --input "$(GPS_CAPTURE)"

# Run the known-vector bench through one full-duplex CP2102.
serial-bench:
	@if [ -z "$(CP2102_PORT)" ] || [ -z "$(CONTEXT_FILE)" ] || [ -z "$(RECEIVED)" ] || [ -z "$(REPORT)" ]; then echo "Uso: make serial-bench CP2102_PORT=/dev/ttyUSB0 CONTEXT_FILE=contexto.json RECEIVED=saida.bin REPORT=relatorio.json [REGISTRY=nonce-registry.json] [TRIALS=4]" >&2; exit 2; fi
	python3 scripts/serial_bench.py run \
		--port "$(CP2102_PORT)" \
		--context "$(CONTEXT_FILE)" \
		--baud "$(or $(BAUD),38400)" \
		--received "$(RECEIVED)" \
		--report "$(REPORT)" $(if $(REGISTRY),--registry "$(REGISTRY)") \
		--trials "$(or $(TRIALS),4)"

manuscript-check:
	python3 scripts/manuscript_check.py

metrics:
	python3 scripts/fpga_metrics.py --json build/de10_lite/metrics.json --markdown build/de10_lite/metrics.md

# Explicit publication selection; use a new filename for each reviewed pair.
metrics-snapshot:
	python3 scripts/fpga_metrics.py --snapshot "$(METRICS_SNAPSHOT)"

# Core-only area/internal timing estimate; virtual ports; no SOF/programming.
aes-fpga:
	bash scripts/quartus_aes_build.sh
