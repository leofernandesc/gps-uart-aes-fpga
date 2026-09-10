create_clock -name clk50 -period 20.000 [get_ports {clk}]
derive_clock_uncertainty
# Standalone, INTERNAL-ONLY timing analysis. There is no upstream/downstream
# circuit yet, and virtual pins are not physical GPIOs. Do not invent zero-delay
# external launches: those incorrectly compete with the physical clock tree.
# These exceptions deliberately exclude boundary paths; they must NOT be copied
# into the future UART/CTR integration, where these ports become internal nets.
set boundary_inputs [get_ports {key_load key_in[*] start block_in[*]}]
set boundary_outputs [get_ports {key_ready key_valid key_done block_ready busy done ciphertext[*]}]
if {[get_collection_size $boundary_inputs] != 258} { error "Unexpected AES input boundary" }
if {[get_collection_size $boundary_outputs] != 134} { error "Unexpected AES output boundary" }
set_false_path -from $boundary_inputs
set_false_path -to $boundary_outputs
set reset_entry [get_registers {*reset_inst|release_pipe[*]}]
if {[get_collection_size $reset_entry] != 2} { error "Expected two reset entry registers" }
set_false_path -from [get_ports {arst}] -to $reset_entry
