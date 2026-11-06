// The delay, drop and corruption operators have to reach the applier as siblings of the command itself, which is
// where NetworkGraph reads them from. Burying them one level deeper still parses, validates and completes, so
// only the payload shape can catch it.
after 2 seconds, change network characteristics
  node "substation_1",
  delay fixed 0.15 seconds,
  drop random 0.25;

after 4 seconds, change network characteristics
  link from "substation_1" to "CC", link from "substation_2" to "CC", node "CC",
  corruption shift_measurement likelihood 0.2 by 0.02;
