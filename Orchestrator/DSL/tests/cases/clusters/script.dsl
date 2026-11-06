// A named cluster reused across statements, an inline list cluster, and a regex cluster resolved against the
// network file. The regex is frozen to its matches on first use, so the payloads show which elements matched.
def load cluster "feeders" ["01_1", "02_1", "03_1"];

after 3 seconds, decrease load cluster "feeders" input "P" by 10%;
after 6 seconds, set load cluster "spares" ["11_1", "12_1"] input "P" to 120;
after 9 seconds, increase load cluster regex "^4[0-9]_1$" on load input "P" by 5%;
