# Provisional internal fit objective only. No board or I/O timing validation.
create_clock -name provisional_clk -period 20.833333 [get_ports clk]
derive_clock_uncertainty
set_false_path -from [get_ports {reset_n rx}]
set_false_path -to [get_ports {tx status[*]}]
