create_clock -name clk50 -period 20.000 [get_ports {MAX10_CLK1_50}]
derive_clock_uncertainty

# Async pins have no phase relationship to clk50. Cut only their entry paths;
# the RX meta->sync chain and synchronized-reset recovery/removal remain timed.
set rx_entry [get_registers {*|rx_inst|rx_meta}]
set reset_entry [get_registers {*reset_inst|release_pipe[*]}]
if {[get_collection_size $rx_entry] != 1} { error "Expected one RX entry register" }
if {[get_collection_size $reset_entry] != 2} { error "Expected two reset synchronizer registers" }
set_false_path -from [get_ports {GPS_RX}] -to $rx_entry
set_false_path -from [get_ports {KEY0_N}] -to $reset_entry

# These outputs do not feed a receiver clocked by clk50. This is an explicit
# asynchronous I/O exception, not a claim of closed external board timing.
# UART bit durations are checked by an independent serial decoder in simulation.
set_false_path -to [get_ports {UART_TX LEDR[*]}]
