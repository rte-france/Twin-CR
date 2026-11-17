"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import grid2op
import numpy as np
import os
import pandas as pd

from grid2op.Agent import DoNothingAgent, PowerLineSwitch, BaseAgent
from grid2op.Action import PlayableAction
from grid2op.gym_compat import GymEnv, DiscreteActSpace, BoxGymObsSpace
from grid2op.Reward import BaseReward
from grid2op.Runner import Runner

from gymnasium import Env
from gymnasium.utils.env_checker import check_env
try:
    from lightsim2grid import LightSimBackend
    bk_cls = LightSimBackend
except ImportError as exc:
    print(f"Error: {exc} when importing faster LightSimBackend")
    from grid2op.Backend import PandaPowerBackend
    bk_cls = PandaPowerBackend

from l2rpn_baselines.utils import GymEnvWithReco, GymEnvWithRecoWithDN

from pathlib import Path
from stable_baselines3 import PPO


pd.options.mode.chained_assignment = None

LEARNING_ITERATION = 500
EVAL_EPISODE = 10
MAX_EVAL_STEPS = 10

# customize the reward function (optional)
class CustomReward(BaseReward):
    def __init__(self, logger=None):
        """
        Initializes :attr:`BaseReward.reward_min` and :attr:`BaseReward.reward_max`

        """
        BaseReward.__init__(self, logger=logger)
        self.reward_min = 0.
        self.reward_max = 1.
        self._min_rho = 0.90
        self._max_rho = 2.0
        
        # parameters init with the environment
        self._max_redisp = None
        self._1_max_redisp = None
        self._is_renew_ = None
        self._1_max_redisp_act = None
        self._nb_renew = None
    
    def initialize(self, env):
        self._max_redisp = np.maximum(env.gen_pmax - env.gen_pmin, 0.)
        self._max_redisp += 1
        self._1_max_redisp = 1.0 / self._max_redisp / env.n_gen
        self._is_renew_ = env.gen_renewable
        self._1_max_redisp_act = np.maximum(np.maximum(env.gen_max_ramp_up, env.gen_max_ramp_down), 1.0)
        self._1_max_redisp_act = 1.0 / self._1_max_redisp_act / np.sum(env.gen_redispatchable)
        self._nb_renew = np.sum(self._is_renew_)
        
    def __call__(self, action, env, has_error, is_done, is_illegal, is_ambiguous):
        if is_done:
            res = np.sqrt(env.nb_time_step / env.max_episode_duration())
            print(f"{os.path.split(env.chronics_handler.get_id())[-1]}: {env.nb_time_step = }, reward : {res:.3f}")
            if env.nb_time_step <= 5:
                print(f"reason game over: {env.infos['exception']}")
            # episode is over => 2 cases
            # if env.nb_time_step == env.max_episode_duration():
            #     return self.reward_max
            # else:
            #     return self.reward_min
            return res
        
        if is_illegal or is_ambiguous or has_error:
            return self.reward_min
        # penalize the dispatch
        obs = env.get_obs()
        score_redisp_state = 0.
        # score_redisp_state = np.sum(np.abs(obs.target_dispatch) * self._1_max_redisp)
        score_redisp_action = np.sum(np.abs(action.redispatch) * self._1_max_redisp_act) 
        score_redisp = 0.5 *(score_redisp_state + score_redisp_action)
        
        # penalize the curtailment
        score_curtail_state = 0.
        # score_curtail_state = np.sum(obs.curtailment_mw * self._1_max_redisp)
        curt_act = action.curtail
        score_curtail_action = np.sum(curt_act[curt_act != -1.0]) / self._nb_renew 
        score_curtail = 0.5 * (score_curtail_state + score_curtail_action)
        
        # rate the actions
        score_action = 0.5 * (np.sqrt(score_redisp) + np.sqrt(score_curtail))
        
        # score the "state" of the grid
        # tmp_state = np.minimum(np.maximum(obs.rho, self._min_rho), self._max_rho)
        # tmp_state -= self._min_rho
        # tmp_state /= (self._max_rho - self._min_rho) * env.n_line
        # score_state = np.sqrt(np.sqrt(np.sum(tmp_state)))
        score_state = 0.

        # score close to goal
        score_goal = 0.
        # score_goal = env.nb_time_step / env.max_episode_duration()
        # score_goal = 1.0
        
        # score too much redisp
        res = score_goal * (1.0 - 0.5 * (score_action + score_state))
        return score_goal * res

class MyPPOAgent(BaseAgent):
    def __init__(self,
                 action_space,  # grid2op action space
                 used_trained_gym_env,  # gym env used for training
                 trained_ppo_nnet,  # neural net after training
                 ):
        super().__init__(action_space)
        self.nn_model = trained_ppo_nnet
        self.gym_env = used_trained_gym_env
    
    def act(self, observation, reward, done=False):
        gym_obs = self.gym_env.observation_space.to_gym(observation)
        gym_act, _ = self.nn_model.predict(gym_obs, deterministic=True)
        grid2op_act = self.gym_env.action_space.from_gym(gym_act)
        return grid2op_act
    
env_name = "l2rpn_case14_sandbox"
training_env = grid2op.make(env_name + "_train", backend=bk_cls(), reward_class=CustomReward) 
gym_env = GymEnvWithRecoWithDN(training_env, safe_max_rho=0.9)

gym_env.action_space = DiscreteActSpace(training_env.action_space,
                                        attr_to_keep=["set_bus" , "set_line_status_simple"])

gym_env.observation_space = BoxGymObsSpace(training_env.observation_space,
                                           attr_to_keep=["rho"])

check_env(gym_env)

obs = gym_env.reset()

nn_model = PPO(env=gym_env,
               learning_rate=3e-4,
               policy="MlpPolicy",
               policy_kwargs={"net_arch": [200, 200, 200, 200]},
               n_steps=2,
               batch_size=8,
               verbose=True,
               gamma=0.999,
               )

nn_model.learn(total_timesteps=LEARNING_ITERATION, progress_bar=True)

nn_model.save(Path("trainer_agent") / "test")

my_agent = MyPPOAgent(training_env.action_space, gym_env, nn_model)
testing_env = grid2op.make(env_name + "_test", backend=bk_cls()) 

import shutil
from tqdm import tqdm
from grid2op.Runner import Runner

save_path = "saved_agent_PPO_{}".format(LEARNING_ITERATION)
path_save_results = "{}_results".format(save_path)
shutil.rmtree(path_save_results, ignore_errors=True)

test_runner = Runner(**testing_env.get_params_for_runner(),
                     agentInstance=my_agent, agentClass=None)
res = test_runner.run(nb_episode=EVAL_EPISODE,
                      max_iter=MAX_EVAL_STEPS,
                      pbar=tqdm,
                      path_save=f"./{path_save_results}")

for _, chron_name, cum_reward, nb_time_step, max_ts in res:
    msg_tmp = "chronics at: {}".format(chron_name)
    msg_tmp += "\ttotal score: {:.6f}".format(cum_reward)
    msg_tmp += "\ttime steps: {:.0f}/{:.0f}".format(nb_time_step, max_ts)
    print(msg_tmp)

# nm_env_train, nm_env_val, nm_env_test = env.train_val_split_random(pct_val=1., pct_test=1., add_for_test="test")
# print(f"The name of the training environment is \\\"{nm_env_train}\\\"")
# print(f"The name of the validation environment is \\\"{nm_env_val}\\\"")
# print(f"The name of the test environment is \\\"{nm_env_test}\\\"")