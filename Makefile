.PHONY: check test lint synth reference bridge aes ctr integration integration-gps pc context gps-replay gps-capture-check manuscript-check metrics cyclone4-metrics fpga baseline-fpga secure-fpga cyclone4-uart-fpga cyclone4-j3-uart-fpga cyclone4-baseline-fpga cyclone4-secure-fpga aes-fpga uart uart-waves uart-fpga de10-nano-uart-fpga

BOARD ?= de10_lite
DESIGN ?= bridge

.PHONY: cyclone4-capacity
# Provisional EP4CE6 / 48 MHz resource study, NOT a board/programming target.
cyclone4-capacity:
	python3 scripts/cyclone4_capacity.py

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

cyclone4-uart-fpga:
	bash scripts/quartus_build.sh cyclone4 uart_scope

# UART scope test with TX/RX routed to accessible J3 PIN_100/PIN_103.
cyclone4-j3-uart-fpga:
	bash scripts/quartus_build.sh cyclone4 j3_scope

cyclone4-baseline-fpga:
	CONTEXT_FILE="$(CONTEXT_FILE)" bash scripts/quartus_build.sh cyclone4 baseline

cyclone4-secure-fpga:
	CONTEXT_FILE="$(CONTEXT_FILE)" bash scripts/quartus_build.sh cyclone4 secure

aes:
	bash scripts/hdl.sh aes

ctr:
	bash scripts/hdl.sh ctr

integration:
	bash scripts/hdl.sh integration

# Full public NMEA replay at the production 50 MHz/9600 baud timing; slower
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

manuscript-check:
	python3 scripts/manuscript_check.py

metrics:
	python3 scripts/fpga_metrics.py --json build/de10_lite/metrics.json --markdown build/de10_lite/metrics.md

cyclone4-metrics:
	python3 scripts/fpga_metrics.py --board cyclone4 --build-root build/cyclone4 \
		--json build/cyclone4/metrics.json --markdown build/cyclone4/metrics.md

# Core-only area/internal timing estimate; virtual ports; no SOF/programming.
aes-fpga:
	bash scripts/quartus_aes_build.sh
