// Two ramps on the same input inside one function body. A body is expanded into a single batch and committed as a
// whole, so the conflict check used to see neither of them, while the same two lines written at top level were
// rejected because each statement commits before the next is read.
func twoRamps(feeder) {
  after [0 seconds, 4 seconds] with law linear, decrease load $feeder input "P" by 20%;
  after [1 seconds, 5 seconds] with law linear, increase load $feeder input "P" by 50%;
}

after 2 seconds, twoRamps("01_1");
