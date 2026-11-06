// Editing a child of a function call. The replacement has to keep the old event's place: it is still that call's
// child, and it still owns the tag the old event was tagged with, so the 'after' below fires when it completes.
// The replacement text here deliberately drops the tag, since the tag belongs to the slot rather than to the text.
func stagedIsolation(breaker, feeder) {
  after 6 seconds, open switch $breaker tagged "breaker_opened";
  after "breaker_opened" is completed, set load $feeder input "P" to 60;
}

after 2 seconds, stagedIsolation("01_1_breaker", "01_1");
