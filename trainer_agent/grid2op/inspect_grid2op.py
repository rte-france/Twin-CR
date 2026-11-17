"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import copy
import csv
import grid2op
from grid2op import make
from grid2op.Agent import DoNothingAgent
from grid2op.Parameters import Parameters
from tqdm import tqdm

from contingency_finder import pp_opf

params = Parameters()
#params.NO_OVERFLOW_DISCONNECTION = True  # prevent game over from overloads
#env = make("l2rpn_case14_sandbox", param=params)
env = make("l2rpn_wcci_2020")  # create an environment
agent = DoNothingAgent(env.action_space)  # create an BaseAgent

obs = env.reset()  # it is necessary to perform a reset
#env.fast_forward_chronics(807)
pp_net = copy.deepcopy(env.backend._grid)
#converged, difficulty, cost = pp_acopf(pp_net)

PI = (pp_net.res_bus["vm_pu"] - 1) / (pp_net.bus["max_vm_pu"] - 1)
PI = PI[pp_net.bus["in_service"]]
reward = env.reward_range[0]
done = False
j = 0
while not done:
    #act = agent.act(obs, reward, done)
    obs, reward, done, info = env.step(env.action_space())
    j += 1

    pp_net = copy.deepcopy(env.backend._grid)
    converged, difficulty, cost = pp_opf(pp_net)
    if difficulty != 0:
        pass


