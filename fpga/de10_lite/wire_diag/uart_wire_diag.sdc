create_clock -name clk50 -period 20.000 [get_ports {MAX10_CLK1_50}]
derive_clock_uncertainty

# This temporary pin-to-pin path is asynchronous and used only for continuity.
set_false_path -from [get_ports {UART_RX}] -to [get_ports {UART_TX}]
set_false_path -to [get_ports {LEDR0}]
