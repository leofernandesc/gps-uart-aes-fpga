# Supplemental STA only: never exports assignments or programs a device.
package require ::quartus::project
package require ::quartus::sta
if {[llength $quartus(args)] != 2} { error "Expected project and new report directory" }
lassign $quartus(args) project out
project_open $project
create_timing_netlist
read_sdc
update_timing_netlist
set corner 0
foreach_in_collection op [get_available_operating_conditions] {
    set_operating_conditions $op
    update_timing_netlist
    incr corner
    report_min_pulse_width -nworst 10 -file $out/min_pulse_width_corner${corner}.rpt
    set checks [get_min_pulse_width -nworst 1]
    if {[llength $checks] != 1} { error "Missing minimum pulse width coverage" }
    set slack [lindex [lindex $checks 0] 0]
    if {![string is double -strict $slack] || $slack < 0} {
        error "Minimum pulse width failed: $slack"
    }
    puts "REVIEW corner=$corner check=min_pulse_width slack_ns=$slack"
    report_metastability -nchains 10 -file $out/metastability_corner${corner}.rpt
}
if {$corner != 3} { error "Expected three MAX 10 timing corners" }
delete_timing_netlist
project_close
puts "PASS: $corner supplemental timing corners audited"
