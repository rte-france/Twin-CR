"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import grid2op
import multiprocessing
import pandas as pd

from lightsim2grid import LightSimBackend
from grid2op.Chronics import MultifolderWithCache  # highly recommended for training
from grid2op.Environment import SingleEnvMultiProcess
from pathlib import Path
from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize

from l2rpn_baselines.PPO_SB3 import train, evaluate
from l2rpn_baselines.utils import GymEnvWithReco, GymEnvWithRecoWithDN

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="test")
    args = parser.parse_args()

    pd.options.mode.chained_assignment = None
     
    env = grid2op.make("l2rpn_case14_sandbox_train", backend=LightSimBackend())
    eval_env = grid2op.make("l2rpn_case14_sandbox_val", backend=LightSimBackend())
    xxx_steps = 2048
    save_path = Path("/Users/martin/sources/RTE/experiments")
    res = train(env, name=args.name, net_arch=[256, 256, 256], gymenv_class=GymEnvWithRecoWithDN, save_path=save_path, iterations=1e8, verbose=True, logs_dir=save_path, save_every_xxx_steps=xxx_steps,
            eval_every_xxx_steps=xxx_steps, eval_env=eval_env)
    # trained_agent, res_eval = evaluate(env, load_path="/Users/martin/sources/RTE/TwinEU-core/trainer_agent", nb_episode=10, verbose=True)
    # trained_agent, res_eval = evaluate(env, name="FirstAgent", load_path="/Users/martin/sources/RTE/l2rpn-baselines/examples/ppo_stable_baselines/saved_model_2023", nb_episode=10, verbose=True)
