"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import copy
from contingency_finder import pp_opf
import grid2op
import math
import pandapower as pp

from grid2op import make
from grid2op.Action import DontAct
from grid2op.Opponent import BaseOpponent, NeverAttackBudget
from grid2op.Parameters import Parameters
from pandapower.contingency import run_contingency

from contingency_finder import pp_opf

params = Parameters()
# params.NO_OVERFLOW_DISCONNECTION = True  # prevent game over from overloads
# params.ENV_DC = True
#env = make("l2rpn_case14_sandbox", param=params)
# Disable opponent and maintenance
env = make("l2rpn_wcci_2020", opponent_attack_cooldown=999999,
                                opponent_attack_duration=0,
                                opponent_budget_per_ts=0,
                                opponent_init_budget=0,
                                opponent_action_class=DontAct,
                                opponent_class=BaseOpponent,
                                opponent_budget_class=NeverAttackBudget, 
                                data_feeding_kwargs={"gridvalueClass": grid2op.Chronics.GridStateFromFileWithForecasts}, # Flagged as internal but did not find other way to do that
                                param=params)

# obs = env.reset(options={"time serie id": "Scenario_december_045", "init ts": 1016})
#obs = env.reset(options={"time serie id": "Scenario_april_019", "init ts": 1})
obs = env.reset(options={"time serie id": "Scenario_april_018", "init ts": 19})


pp_net = copy.deepcopy(env.backend._grid)

thermal_limits = env.get_thermal_limit()
pp_net.line["max_i_ka"] = thermal_limits[:len(pp_net.line["max_i_ka"])] / 1000
pp_net.trafo["sn_mva"] = math.sqrt(3) * pp_net.trafo["vn_hv_kv"] * thermal_limits[len(pp_net.line["max_i_ka"]):] / 1000
pp_net.res_line["loading_percent"] = pp_net.res_line["i_ka"] / pp_net.line["max_i_ka"] * 100
pp_net.res_trafo["loading_percent"] = pp_net.res_trafo["i_hv_ka"] * pp_net.trafo["vn_hv_kv"] / pp_net.trafo["sn_mva"] * 100

converged, difficulty, cost, p_redispatch = pp_opf(pp_net)
print("init", converged, difficulty, cost)
prev_line_id = None
# nminus1_cases = {"line": {"index": pp_net.line.index}, "trafo": {"index": pp_net.trafo.index}}

for line_id in pp_net.line.index:
    pp_net.line.loc[line_id, "in_service"] = False
    if prev_line_id is not None:
        pp_net.line.loc[prev_line_id, "in_service"] = True
    prev_line_id = line_id
    # res = run_contingency(pp_net, nminus1_cases)
    # print(line_id, res["line"]["causes_overloading"].any())
    converged, difficulty, cost, p_redispatch = pp_opf(pp_net)
    print(line_id, converged, difficulty, cost)

prev_trafo_id = None
for trafo_id in pp_net.trafo.index:
    pp_net.trafo.loc[trafo_id, "in_service"] = False
    if prev_trafo_id is not None:
        pp_net.trafo.loc[prev_trafo_id, "in_service"] = True
    prev_trafo_id = trafo_id
    # res = run_contingency(pp_net, nminus1_cases)
    # print(trafo_id, res["line"]["causes_overloading"].any())
    converged, difficulty, cost, p_redispatch = pp_opf(pp_net)
    print(trafo_id, converged, difficulty, cost)


print()
