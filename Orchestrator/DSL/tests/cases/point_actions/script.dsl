// Point actions: switch and line state, an absolute set, and a percentage adjustment.
// Covers time resolution (s / min abbreviations), tags, and multi-element targets.
after 2 seconds, open switch "01_1_breaker" tagged "load_1_isolated";
after 5 seconds, close switch "01_1_breaker";
after 8 seconds, open transformer "Tr1011-4011";
after 10 s, set load "02_1" input "P" to 250;
after 15 s, decrease load ["03_1", "04_1"] input "P" by 5%;
after "load_1_isolated" is completed, increase load "05_1" input "P" by 10%;
