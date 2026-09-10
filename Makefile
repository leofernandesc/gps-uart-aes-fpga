.PHONY: check test lint synth reference bridge aes ctr fpga aes-fpga

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
	bash scripts/quartus_build.sh

aes:
	bash scripts/hdl.sh aes

ctr:
	bash scripts/hdl.sh ctr

# Core-only area/internal timing estimate; virtual ports; no SOF/programming.
aes-fpga:
	bash scripts/quartus_aes_build.sh
