// Every kind of value a parameter can hold has to survive being passed in and used inside the body: a string, a
// number, and a parameter forwarded on to a second function, which is the case a caller cannot work around since
// a parameter has no other spelling. Arguments carry no element type. The callee supplies it where it uses the
// value, so the same string reaches a switch, a load, a cluster, an input type and a tag depending on the body.
func openOne(breaker) {
  after 0 seconds, open switch $breaker;
}

func openPair(left, right) {
  openOne($left);
  openOne($right);
}

func trim(group, attribute, amount) {
  after 0 seconds, decrease load cluster $group input $attribute by $amount%;
}

func trimThenIsolate(feeder, attribute, label) {
  after 0 seconds, decrease load $feeder input $attribute by 5% tagged $label;
  after $label is completed, open switch "04_1_breaker";
}

def load cluster "feeders" ["01_1", "02_1"];

after 2 seconds, openOne("01_1_breaker");
after 5 seconds, openPair("02_1_breaker", "03_1_breaker");
after 8 seconds, trim("feeders", "P", 10);
after 11 seconds, trimThenIsolate("03_1", "P", "trimmed");
