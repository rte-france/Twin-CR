"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import grid2op
import numpy as np
from lightsim2grid import LightSimBackend
from grid2op.Runner import Runner

if __name__ == "__main__":
    env = grid2op.make("l2rpn_case14_sandbox_val", backend=LightSimBackend())

    runner_params = env.get_params_for_runner()
    runner = Runner(**runner_params)

    res = runner.run(nb_episode=42,
                    nb_process=10
                    )

    # Print summary
    print("Evaluation summary for Do Nothing:")
    for _, chron_name, cum_reward, nb_time_step, max_ts in res:
        msg_tmp = "chronics at: {}".format(chron_name)
        msg_tmp += "\ttotal score: {:.6f}".format(cum_reward)
        msg_tmp += "\ttime steps: {:.0f}/{:.0f}".format(nb_time_step, max_ts)
        print(msg_tmp)

    res = np.array(res)
    res = np.float64(res[:, 2:4])
    mean_rew = np.mean(res[:, 0])
    mean_ep_len = np.mean(res[:, 1])
    print("Mean reward:", mean_rew)
    print("Mean ep len:", mean_ep_len)