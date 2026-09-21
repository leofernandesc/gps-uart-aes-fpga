# Candidate ZRTech/WXEDA V2.00 profile: 48 MHz oscillator.
create_clock -name clk48 -period 20.833333 [get_ports {CLOCK_48}]
derive_clock_uncertainty

set rx_entry [get_registers {*|rx_inst|rx_meta}]
set reset_entry [get_registers {*reset_inst|release_pipe[*]}]
if {[get_collection_size $rx_entry] != 1} { error "Expected one RX entry register" }
if {[get_collection_size $reset_entry] != 2} { error "Expected two reset synchronizer registers" }
set_false_path -from [get_ports {UART_RX}] -to $rx_entry
set_false_path -from [get_ports {RESET_N}] -to $reset_entry
set_false_path -to [get_ports {UART_TX LED[*]}]
