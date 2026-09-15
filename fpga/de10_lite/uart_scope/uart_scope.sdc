create_clock -name clk50 -period 20.000 [get_ports {MAX10_CLK1_50}]
derive_clock_uncertainty

# External UART and pushbutton have no synchronous phase relationship to clk50.
# The synchronizer's internal paths and reset recovery/removal remain timed.
set rx_entry [get_registers {*|rx_inst|rx_meta}]
set reset_entry [get_registers {*reset_inst|release_pipe[*]}]
if {[get_collection_size $rx_entry] != 1} { error "Expected one RX entry register" }
if {[get_collection_size $reset_entry] != 2} { error "Expected two reset synchronizer registers" }
set_false_path -from [get_ports {UART_RX}] -to $rx_entry
set_false_path -from [get_ports {KEY0_N}] -to $reset_entry
set_false_path -to [get_ports {UART_TX LEDR[*]}]
