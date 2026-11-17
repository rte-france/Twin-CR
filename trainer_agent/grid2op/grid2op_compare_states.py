"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import copy
import grid2op
import math

from grid2op import make
from grid2op.Action import DontAct
from grid2op.Opponent import BaseOpponent, NeverAttackBudget
from grid2op.Parameters import Parameters

def get_pp_net_from_env(env):
    thermal_limits = env.get_thermal_limit()

    pp_net = copy.deepcopy(env.backend._grid)                
    pp_net.line["max_i_ka"] = thermal_limits[:len(pp_net.line["max_i_ka"])] / 1000
    # Changing sn_mva directly has an influence on impedance (as impedance is relative vk_percent etc)
    s_max_mva = math.sqrt(3) * pp_net.trafo["vn_lv_kv"] * thermal_limits[len(pp_net.line["max_i_ka"]):] / 1000
    pp_net.trafo["max_loading_percent"] = 100.0 * s_max_mva / pp_net.trafo["sn_mva"]

    pp_net.gen["max_p_mw"] = env.gen_pmax

    return pp_net

if __name__ == "__main__":
    params = Parameters()
    # params.NO_OVERFLOW_DISCONNECTION = True  # prevent game over from overloads
    #params.ENV_DC = True
    #env = make("l2rpn_neurips_2020_track2_large", param=params)
    # Disable opponent and maintenance
    env = make("l2rpn_idf_2023", opponent_attack_cooldown=999999,
                                    opponent_attack_duration=0,
                                    opponent_budget_per_ts=0,
                                    opponent_init_budget=0,
                                    opponent_action_class=DontAct,
                                    opponent_class=BaseOpponent,
                                    opponent_budget_class=NeverAttackBudget, 
                                    data_feeding_kwargs={"gridvalueClass": grid2op.Chronics.GridStateFromFileWithForecasts}, # Flagged as internal but did not find other way to do that
                                    param=params)

    # obs = env.reset(options={"time serie id": "Scenario_december_045", "init ts": 1016})
    # obs = env.reset(options={"time serie id": "Scenario_april_019", "init ts": 1})
    obs = env.reset()#options={"time serie id": "Scenario_april_010", "init ts": 700})

    prev_pp_net = get_pp_net_from_env(env)

    obs = env.reset(options={"time serie id": "2035-01-08_0", "init ts": 1})

    pp_net = get_pp_net_from_env(env)

    # This is events that occur on the grid
    pp_net.gen["p_mw"] - prev_pp_net.gen["p_mw"]
    pp_net.load["p_mw"] - prev_pp_net.load["p_mw"]
    # probably this one will not change
    pp_net.line["in_service"]

