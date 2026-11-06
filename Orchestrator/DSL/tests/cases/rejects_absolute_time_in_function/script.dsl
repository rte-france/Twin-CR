// A function is invoked at an arbitrary time, so an absolute time in its body would pin it to one moment.
// Only 'after' is accepted there.
func isolate(breaker) {
  at 30 seconds, open switch $breaker;
}
after 5 seconds, isolate("01_1_breaker");
