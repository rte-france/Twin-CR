// The script only has to establish what there is to suggest: a function to offer by name, a cluster to offer
// inside a cluster slot, and a body whose parameters are what a '$' completes to.
def load cluster "feeders" ["01_1", "02_1"];

func isolateFeeder(breaker, feeder) {
  after 0 seconds, open switch $breaker;
}
