// Inputs on purely dynamic models, which have no equipmentId and are named by their model library and model
// instead. Covers the three target forms, a point set, a percentage adjustment and a value ramp, plus a model
// reached through a function parameter.
after 2 seconds, set "DYNModelRST" "RST_4011" input "U" to 400;
after 5 seconds, decrease "DYNModelRST" "RST_4011" input "deltaU" by 10%;
after [8 seconds, 10 seconds] with law linear, set "DYNModelRST" "RST_4012" input "U" from 400 to 410;

func raise(regulator) {
  after 2 seconds, increase "DYNModelRST" $regulator input "U" by 5%;
}
after 14 seconds, raise("RST_4011");

// Grouping works as it does for IIDM elements: a list, and a cluster whose regex matches the models the
// mapping can address.
after 12 seconds, set "DYNModelRST" ["RST_4011", "RST_4012"] input "U" to 402;
def "DYNModelRST" cluster "regulators" regex "^RST_401" on "DYNModelRST";
after 18 seconds, increase "DYNModelRST" cluster "regulators" input "U" by 1%;

// A condition reads a dynamic model's output the same way an action writes its input
when "DYNModelOmegaRef" "OmegaRef" output "OmegaRef" < 49.8, set "DYNModelRST" "RST_4011" input "deltaU" to 2;
