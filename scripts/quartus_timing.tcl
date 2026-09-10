package require ::quartus::project
package require ::quartus::sta
project_open uart_bridge
create_timing_netlist
read_sdc
update_timing_netlist
set out ../../build/quartus
report_clocks -file $out/clocks.rpt
check_timing -file $out/check_timing.rpt
report_ucp -file $out/unconstrained.rpt
report_exceptions -file $out/exceptions.rpt
report_metastability -file $out/metastability.rpt

set failed 0
# check_timing lists missing synchronous I/O delays even for deliberately
# excepted asynchronous pins. Only those exact, documented findings are allowed.
set report [open $out/check_timing.rpt r]
set contents [read $report]
close $report
set checked 0
foreach line [split $contents "\n"] {
    if {[regexp {^;\s+([a-z_]+)\s+;\s+([0-9]+)\s+;} $line -> check count]} {
        incr checked
        set expected 0
        switch -- $check {
            virtual_clock { set expected 1 }
            no_input_delay { set expected 2 }
            no_output_delay { set expected 11 }
        }
        if {$count != $expected} {
            puts "AUDIT unexpected check_timing result: $check=$count (expected $expected)"
            set failed 1
        }
    }
}
if {$checked < 20} { error "Could not parse check_timing summary" }
set report [open $out/unconstrained.rpt r]
set contents [read $report]
close $report
set checked 0
foreach line [split $contents "\n"] {
    if {[regexp {^;\s+(Illegal Clocks|Unconstrained[^;]+)\s+;\s+([0-9]+)\s+;\s+([0-9]+)\s+;} $line -> kind setup hold]} {
        incr checked
        if {$setup != 0 || $hold != 0} {
            puts "AUDIT unconstrained paths: $kind setup=$setup hold=$hold"
            set failed 1
        }
    }
}
if {$checked != 6} { error "Could not parse unconstrained paths summary" }

set corner_index 0
foreach_in_collection op [get_available_operating_conditions] {
    set_operating_conditions $op
    update_timing_netlist
    incr corner_index
    report_clock_fmax_summary -file $out/fmax_corner${corner_index}.rpt
    foreach analysis {setup hold recovery removal} {
        report_timing -$analysis -npaths 10 -detail full_path -file $out/${analysis}_corner${corner_index}.rpt
        set paths [get_timing_paths -$analysis -npaths 1]
        if {[get_collection_size $paths] == 0} { error "No $analysis paths: timing coverage missing" }
        foreach_in_collection path $paths {
            set slack [get_path_info -slack $path]
            puts "AUDIT corner=$corner_index check=$analysis slack_ns=$slack"
            if {$slack < 0} { set failed 1 }
        }
    }
}
if {$corner_index == 0} { error "No operating conditions audited" }
delete_timing_netlist
project_close
if {$failed} { error "Timing/constraint audit failed: inspect reports" }
puts "PASS: $corner_index timing corners audited"
