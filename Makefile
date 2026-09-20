.PHONY: check test lint synth reference bridge aes ctr integration pc context fpga baseline-fpga secure-fpga aes-fpga uart uart-waves uart-fpga de10-nano-uart-fpga

BOARD ?= de10_lite
DESIGN ?= bridge

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
	bash scripts/quartus_build.sh de10_lite baseline

secure-fpga:
	bash scripts/quartus_build.sh de10_lite secure

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

pc:
	python3 -m unittest discover -s tb -p 'test_*.py' -v

context:
	python3 -m unittest discover -s tb -p 'test_context.py' -v

# Core-only area/internal timing estimate; virtual ports; no SOF/programming.
aes-fpga:
	bash scripts/quartus_aes_build.sh
