"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import copy
import csv
import grid2op
import math
import pandapower as pp
import re
from grid2op import make
from grid2op.Action import DontAct
from grid2op.Opponent import BaseOpponent, NeverAttackBudget
from grid2op.Parameters import Parameters
import multiprocessing as mp
import numpy as np
from tqdm import tqdm

from opf import pp_opf
from trainer_agent.grid2op.grid2op_compare_states import get_pp_net_from_env
from lightsim2grid import LightSimBackend

def compute_difficulty(idx):
    params = Parameters()
    params.NO_OVERFLOW_DISCONNECTION = True  # prevent game over from overloads
    # params.ENV_DC = True
    #env = make("l2rpn_case14_sandbox", param=params)
    # Disable opponent and maintenance
    #make("l2rpn_neurips_2020_track2_large")
    env = make("l2rpn_wcci_2020", opponent_attack_cooldown=999999,
                                    opponent_attack_duration=0,
                                    opponent_budget_per_ts=0,
                                    opponent_init_budget=0,
                                    opponent_action_class=DontAct,
                                    opponent_class=BaseOpponent,
                                    opponent_budget_class=NeverAttackBudget, 
                                    data_feeding_kwargs={"gridvalueClass": grid2op.Chronics.GridStateFromFileWithForecasts}, # Flagged as internal but did not find other way to do that
                                    param=params)
    thermal_limits = env.get_thermal_limit()

    if idx > -1:
        env.chronics_handler.set_filter(lambda path: re.match(f".*{idx}$", path) is not None)
        env.chronics_handler.reset()
        nb_episodes = np.sum([re.match(f".*{idx}$", path) is not None for path in env.chronics_handler.subpaths])

    else:
        idx= ""
        nb_episodes = len(env.chronics_handler.subpaths)

    #env.chronics_handler.shuffle()
    with open(f"scenarios{idx}.csv", "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["name", "chronic", "time_step", "v_PI"])
        # csv_writer.writerow(["name", "chronic", "time_step", "j", "previous_clean_state", "difficulty", "cost", 
        #                      "overflow_PI", "v_PI", "redispatch"])
        for i in tqdm(range(nb_episodes)):
            #_ = env.chronics_handler.sample_next_chronics()
            #env.seed(42)  # must be before each reset — maintenance is regenerated on every reset
            obs = env.reset()#options={"time serie id": "Scenario_april_024"})#, "init ts": 1600})  # it is necessary to perform a reset

            # env.fast_forward_chronics(1600)
            # pp_net = copy.deepcopy(env.backend._grid)                

            # pp_net = get_pp_net_from_env(env)

            # converged, difficulty, cost, p_redispatch = pp_opf(pp_net)

            done = False
            j = 0
            previous_clean_state = -1
            while not done:
                obs, reward, done, info = env.step(env.action_space())
                j += 1
                # total_gen = np.sum(obs.gen_p)
                # total_load = np.sum(obs.load_p)
                # csv_writer.writerow([env.chronics_handler.get_name(), i, env.nb_time_step, j, total_gen, total_load])
                # pp_net = get_pp_net_from_env(env)
                pp_net = copy.deepcopy(env.backend._grid)                

                # pp_net.res_line["loading_percent"] = pp_net.res_line["i_ka"] / pp_net.line["max_i_ka"] * 100
                # pp_net.res_trafo["loading_percent"] = pp_net.res_trafo["i_hv_ka"] * pp_net.trafo["vn_hv_kv"] / pp_net.trafo["sn_mva"] * 100
                
                overvoltages_idx = pp_net.res_bus["vm_pu"] > pp_net.bus["max_vm_pu"]
                bus_PI = (pp_net.res_bus["vm_pu"] - 1) / (pp_net.bus["max_vm_pu"] - 1)
                bus_PI = bus_PI[pp_net.bus["in_service"] & overvoltages_idx]
                bus_PI = bus_PI ** 2

                # overflows_idx = pp_net.res_line["loading_percent"] > 100
                # line_PI = pp_net.res_line["loading_percent"][pp_net.line["in_service"] & overflows_idx] / 100
                # line_PI = line_PI ** 2

                # overflows_idx = pp_net.res_trafo["loading_percent"] > 100
                # trafo_PI = pp_net.res_trafo["loading_percent"][pp_net.trafo["in_service"] & overflows_idx] / 100
                # trafo_PI = trafo_PI ** 2

                # overflow_PI = line_PI.sum() + trafo_PI.sum()


                # # Am I missing a condition here ?
                # if not ((pp_net.res_line["loading_percent"] > 100).any() or 
                #         (pp_net.res_trafo["loading_percent"] > 100).any() or 
                #         (pp_net.res_gen["p_mw"] > pp_net.gen["max_p_mw"]).any() or 
                #         (pp_net.res_gen["p_mw"] < pp_net.gen["min_p_mw"]).any()):
                #     previous_clean_state = j
                #     continue

                # converged, difficulty, cost, p_redispatch = pp_opf(pp_net)
                #print(j, env.nb_time_step)

                # if difficulty > 0:
                #     print()
                if True or difficulty != 0:
                    csv_writer.writerow([env.chronics_handler.get_name(), i, env.nb_time_step, bus_PI.sum()])
                    # csv_writer.writerow([env.chronics_handler.get_name(), i, env.nb_time_step, j, 
                    #                      previous_clean_state, difficulty, cost, overflow_PI, bus_PI.sum(), 
                    #                      p_redispatch.to_list()])
                    # f.flush()
                else:
                    previous_clean_state = j

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parallel", action="store_true")

    args = parser.parse_args()

    if args.parallel:
        pool = mp.Pool(10)
        pool.map(compute_difficulty, range(10))

    else:
        compute_difficulty(-1)
