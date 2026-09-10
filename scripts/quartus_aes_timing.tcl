package require ::quartus::project
package require ::quartus::sta
project_open aes128_analysis
create_timing_netlist
read_sdc
update_timing_netlist
set out ../../build/quartus_aes
report_clocks -file $out/clocks.rpt
check_timing -file $out/check_timing.rpt
report_ucp -file $out/unconstrained.rpt
report_exceptions -file $out/exceptions.rpt
set failed 0
set report [open $out/check_timing.rpt r]
set contents [read $report]
close $report
set checked 0
foreach line [split $contents "\n"] {
    if {[regexp {^;\s+([a-z_]+)\s+;\s+([0-9]+)\s+;} $line -> check count]} {
        incr checked
        set expected 0
        # Standalone virtual boundaries are explicitly excluded in the SDC.
        # This is an internal timing audit, not interface timing closure.
        switch -- $check {
            virtual_clock { set expected 1 }
            no_input_delay { set expected 259 }
            no_output_delay { set expected 134 }
        }
        if {$count != $expected} {
            puts "AUDIT unexpected constraint check: $check=$count expected=$expected"
            set failed 1
        }
    }
}
if {$checked < 20} { error "Missing check_timing coverage" }
set report [open $out/unconstrained.rpt r]
set contents [read $report]
close $report
set checked 0
foreach line [split $contents "\n"] {
    if {[regexp {^;\s+(Illegal Clocks|Unconstrained[^;]+)\s+;\s+([0-9]+)\s+;\s+([0-9]+)\s+;} $line -> kind setup hold]} {
        incr checked
        if {$setup != 0 || $hold != 0} { set failed 1 }
    }
}
if {$checked != 6} { error "Missing unconstrained paths coverage" }
set corner 0
foreach_in_collection op [get_available_operating_conditions] {
    set_operating_conditions $op
    update_timing_netlist
    incr corner
    report_clock_fmax_summary -file $out/fmax_corner${corner}.rpt
    foreach analysis {setup hold recovery removal} {
        report_timing -$analysis -npaths 5 -detail full_path -file $out/${analysis}_corner${corner}.rpt
        set paths [get_timing_paths -$analysis -npaths 1]
        if {[get_collection_size $paths] == 0} { error "No $analysis paths" }
        foreach_in_collection path $paths {
            set slack [get_path_info -slack $path]
            puts "AUDIT corner=$corner check=$analysis slack_ns=$slack"
            if {$slack < 0} { set failed 1 }
        }
    }
}
if {$corner != 3} { error "Expected three MAX 10 operating corners" }
delete_timing_netlist
project_close
if {$failed} { error "AES timing/constraint audit failed" }
puts "PASS: AES INTERNAL timing audit, $corner corners; virtual boundary timing excluded"
