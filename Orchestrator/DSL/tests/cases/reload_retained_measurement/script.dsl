// A condition comparing two live values, where one of them was last measured before the dump and never again.
// DSLValueCache serializes its values precisely so a reload does not momentarily lose the last-known reading;
// if it did not, the left side would arrive after the reload and find nothing to compare against.
when load "01_1" output "P" > load "02_1" output "P", decrease load "03_1" input "P" by 5%;
