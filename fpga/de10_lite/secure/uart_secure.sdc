create_clock -name clk50 -period 20.000 [get_ports {MAX10_CLK1_50}]
derive_clock_uncertainty

# UART RX and KEY0_N are asynchronous to the 50 MHz clock.  The first RX
# register and reset synchronizer are deliberately excluded from input timing;
# the synchronizer chains and recovery/removal remain timed.
set rx_entry [get_registers {*|bridge_inst|rx_inst|rx_meta}]
set reset_entry [get_registers {*|reset_inst|release_pipe[*]}]
if {[get_collection_size $rx_entry] != 1} { error "Expected one RX entry register" }
if {[get_collection_size $reset_entry] != 2} { error "Expected two reset synchronizer registers" }
set_false_path -from [get_ports {UART_RX}] -to $rx_entry
set_false_path -from [get_ports {KEY0_N}] -to $reset_entry

# UART_TX and LEDs are asynchronous outputs without a board-side clock.  The
# serial bit duration is verified by the UART testbench and oscilloscope.
set_false_path -to [get_ports {UART_TX LEDR[*]}]
