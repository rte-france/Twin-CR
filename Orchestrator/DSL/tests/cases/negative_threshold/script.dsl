// A negative number in a condition. Arithmetic had no sign of its own, so a threshold below zero could only be
// reached by writing '0 - 5', which is not something a user would guess.
when load "01_1" output "P" < -5, open switch "01_1_breaker";
