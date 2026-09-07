.PHONY: check test lint synth reference

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
