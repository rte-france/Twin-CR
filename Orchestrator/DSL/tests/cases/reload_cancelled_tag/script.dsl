// Two events share a tag and a third waits on it. Cancelling one of the owners while it is Ready means the tag can
// never complete, which is the intended reading of a deleted prerequisite. A dump and reload has to preserve that:
// the cancelled owner is gone from the registry, so a tag map rebuilt by walking the registry would no longer know
// the tag was ever waiting on it, and the dependent action would fire on work that never ran.
after 6 seconds, open switch "01_1_breaker" tagged "both_isolated";
after 20 seconds, open switch "02_1_breaker" tagged "both_isolated";
after "both_isolated" is completed, open switch "03_1_breaker";
