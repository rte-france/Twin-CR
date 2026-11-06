// The limit has to hold when the percentage arrives through a parameter, including the case where a negative
// argument turns an 'increase' into a decrease. The check is on the resolved value, not on what was written.
func trim(feeder, amount) {
  after 0 seconds, increase load $feeder input "P" by $amount%;
}

after 2 seconds, trim("01_1", -150);
