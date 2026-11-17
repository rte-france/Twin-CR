"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import argparse
import grid2op
import numpy as np
from pathlib import Path
from torch.utils.tensorboard import SummaryWriter
from lightsim2grid import LightSimBackend
from tqdm import tqdm

from l2rpn_baselines.PPO_SB3 import evaluate
from l2rpn_baselines.utils import GymEnvWithReco, GymEnvWithRecoWithDN

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="/Users/martin/sources/RTE/experiments/20260324_PPO_case14_bigger_arch")
    args = parser.parse_args()

    path = Path(args.name)
    name = path.name
    folder = path.parent
    writer = SummaryWriter(path / "benchmark")

    eval_env = grid2op.make("l2rpn_case14_sandbox", backend=LightSimBackend())
    step = 2048*30
    #for i in tqdm(range(step, 11796480, step*10)):
    # for i in tqdm(range(step*100, 79134720, step*10)):
    for i in tqdm(range(step, 77721601, step*10)):
    # for i in tqdm(range(step, 12963840, step*10)):
        # trained_agent, res_eval = evaluate(eval_env, name="PPO_SB3_case14", load_path="/Users/martin/sources/RTE/experiments", nb_episode=100, verbose=True, iter_num=2328576, nb_process=10)
        # _, res_eval = evaluate(eval_env, name="PPO_SB3_case14_3", load_path="/Users/martin/sources/RTE/experiments", nb_episode=42, verbose=True, iter_num=i, nb_process=10)
        _, res_eval = evaluate(eval_env, gymenv_class=GymEnvWithRecoWithDN, name=name, load_path=folder, nb_episode=42, verbose=True, iter_num=77721600, nb_process=10, logs_path="for_viz")
        res = np.array(res_eval)
        res = np.float64(res[:, 2:4])
        mean_rew = np.mean(res[:, 0])
        mean_ep_len = np.mean(res[:, 1])
        writer.add_scalar("mean_rew", mean_rew, i)
        writer.add_scalar("mean_ep_len", mean_ep_len, i)
        # print("mean_rew", mean_rew, i)
        # print("mean_ep_len", mean_ep_len, i)
        break
