// A trigger whose body is a function call. The call is expanded when the trigger fires, not when it is written,
// so the times inside the body count from the firing. A when_rearming therefore produces a fresh set every time
// it fires, which is the whole reason a staged response is worth expressing this way.
func isolate(breaker, feeder) {
  after 0 seconds, open switch $breaker;
  after 2 seconds, decrease load $feeder input "P" by 10%;
}

when_rearming load "01_1" output "P" > 200, isolate("01_1_breaker", "02_1");
