// A transformer's "lock" input publishes no measurement, so there is nothing to start the ramp from and the
// statement has to say where it starts.
after [2 seconds, 6 seconds], set 2_windings_transformer "Tr1011-4011" input "lock" to 1;
