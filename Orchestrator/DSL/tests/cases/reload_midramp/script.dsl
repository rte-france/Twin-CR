// A ramp that straddles a dump/reload. The engine is dumped at 7.5 s, thrown away, and rebuilt from the dump,
// so the second half of the ramp is driven entirely by what RampEvent serialized: its interval, its targets and
// the cumulative ratio already applied. The per-tick factors must continue the same curve, and the product of
// every factor across both halves must still land exactly on the requested -20%.
after [4 seconds, 12 seconds] with law linear, decrease load "01_1" input "P" by 20%;
