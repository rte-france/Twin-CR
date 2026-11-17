"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import grid2op
env_name = "l2rpn_wcci_2020"  # or any other...
env = grid2op.make(env_name)

# extract 1% of the "chronics" to be used in the validation environment
nm_env_train, nm_env_val, nm_env_test = env.train_val_split_random(pct_val=42./2880*100, pct_test=42./2880*100, add_for_test="test")

print(f"The name of the training environment is \"{nm_env_train}\"")
print(f"The name of the validation environment is \"{nm_env_val}\"")
print(f"The name of the test environment is \"{nm_env_test}\"")