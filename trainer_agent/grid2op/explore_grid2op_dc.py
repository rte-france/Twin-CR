"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import csv
import grid2op
import pandapower as pp
import re
from grid2op import make
from grid2op.Action import DontAct
from grid2op.Opponent import BaseOpponent, NeverAttackBudget
from grid2op.Parameters import Parameters
import multiprocessing as mp
from tqdm import tqdm

from opf import pp_opf
from contingency_finder import compute_overflow_PI
from trainer_agent.grid2op.grid2op_compare_states import get_pp_net_from_env

def compute_bus_PI(pp_net):
    try:
        pp.runpp(pp_net)
        overvoltages_idx = pp_net.res_bus["vm_pu"] > pp_net.bus["max_vm_pu"]
        bus_PI = (pp_net.res_bus["vm_pu"] - 1) / (pp_net.bus["max_vm_pu"] - 1)
        bus_PI = bus_PI[pp_net.bus["in_service"] & overvoltages_idx]
        bus_PI = bus_PI ** 2
        bus_PI = bus_PI.sum()
    except pp.auxiliary.LoadflowNotConverged:
        bus_PI = -1

    return bus_PI

def compute_difficulty(idx):
    params = Parameters()
    params.NO_OVERFLOW_DISCONNECTION = True  # prevent game over from overloads
    # params.ENV_DC = True
    #env = make("l2rpn_case14_sandbox", param=params)
    # Disable opponent and maintenance
    #make("l2rpn_idf_2023")
    env = make("l2rpn_idf_2023", opponent_attack_cooldown=999999,
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
        env.chronics_handler.set_filter(lambda path: re.match(f".*_{idx}$", path) is not None)
        # env.chronics_handler.set_filter(lambda path: re.match(f".*{idx}$", path) is not None)
        chronics = env.chronics_handler.reset()
        nb_episodes = len(chronics)

    else:
        idx= ""
        nb_episodes = len(env.chronics_handler.subpaths)

    with open(f"scenarios{idx}.csv", "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["name", "chronic", "time_step", "j", "previous_clean_state", "difficulty", "cost", 
                             "overflow_PI", "init_v_PI", "sol_v_PI", "redispatch"])
        for i in tqdm(range(nb_episodes)):
            obs = env.reset()

            pp_net = get_pp_net_from_env(env)

            pp_net.bus["min_vm_pu"] = 0.9
            pp_net.bus["max_vm_pu"] = 1.1
            previous_clean_state = -1
            for j in range(env.chronics_handler.real_data.max_iter + 1):
                pp_net.gen["p_mw"] = env.chronics_handler.real_data.data.prod_p[j]
                pp_net.load["p_mw"] = env.chronics_handler.real_data.data.load_p[j]

                overflow_PI = compute_overflow_PI(pp_net)

                # Am I missing a condition here ?
                if not ((pp_net.res_line["loading_percent"] > 100).any() or 
                        (pp_net.res_trafo["loading_percent"] > pp_net.trafo["max_loading_percent"]).any() or 
                        (pp_net.res_gen["p_mw"] > pp_net.gen["max_p_mw"]).any() or 
                        (pp_net.res_gen["p_mw"] < pp_net.gen["min_p_mw"]).any()):
                    previous_clean_state = j
                    continue

                converged, difficulty, cost, p_redispatch = pp_opf(pp_net, True)

                if difficulty != 0:
                    # Compute the overvoltage in the solution of the opf
                    # One way is to reput losses other way is simply consider load stays constant
                    # losses = env.chronics_handler.real_data.data.prod_p[j].sum() - env.chronics_handler.real_data.data.load_p[j].sum()
                    pp_net.gen["p_mw"] = pp_net.res_gen["p_mw"]
                    pp_net.load["p_mw"] = env.chronics_handler.real_data.data.load_p[j]
                    
                    sol_bus_PI = compute_bus_PI(pp_net)

                    # Compute overvoltage in the initial situation
                    pp_net.gen["p_mw"] = env.chronics_handler.real_data.data.prod_p[j]
                    pp_net.load["p_mw"] = env.chronics_handler.real_data.data.load_p[j]
                    
                    init_bus_PI = compute_bus_PI(pp_net)

                    csv_writer.writerow([env.chronics_handler.get_name(), i, env.nb_time_step, j, 
                                         previous_clean_state, difficulty, cost, overflow_PI, init_bus_PI, sol_bus_PI, 
                                         p_redispatch.to_list()])
                    f.flush()
                else:
                    previous_clean_state = j

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parallel", action="store_true")

    args = parser.parse_args()

    if args.parallel:
        n_jobs = 16
        pool = mp.Pool(n_jobs)
        pool.map(compute_difficulty, range(n_jobs))

    else:
        compute_difficulty(-1)
