"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import grid2op
env_name = "l2rpn_wcci_2020"  # or any other...
env = grid2op.make(env_name)

# extract 1% of the "chronics" to be used in the validation environment
nm_env_train, nm_env_val, nm_env_test = env.train_val_split_random(pct_val=42./2880*100, pct_test=42./2880*100, add_for_test="test")

print(f"The name of the training environment is \"{nm_env_train}\"")
print(f"The name of the validation environment is \"{nm_env_val}\"")
print(f"The name of the test environment is \"{nm_env_test}\"")