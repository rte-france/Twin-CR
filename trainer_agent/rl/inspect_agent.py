"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import os

from grid2op.Episode import EpisodeData

LEARNING_ITERATION = 500

save_path = "saved_agent_PPO_{}".format(LEARNING_ITERATION)
path_save_results = "{}_results".format(save_path)

EpisodeData.list_episode(path_save_results)
all_episodes = EpisodeData.list_episode(path_save_results)
this_episode = EpisodeData.from_disk(*all_episodes[0])
li_actions = this_episode.actions



line_disc = 0
line_reco = 0
for act in li_actions:
    dict_ = act.as_dict()
    if "set_line_status" in dict_:
        line_reco +=  dict_["set_line_status"]["nb_connected"]
        line_disc +=  dict_["set_line_status"]["nb_disconnected"]
print(f'Total reconnected lines : {line_reco}')
print(f'Total disconnected lines : {line_disc}')

li_observations = this_episode.observations
nb_real_disc = 0
for obs_ in li_observations:
    nb_real_disc += (obs_.line_status == False).sum()
print(f'Total number of disconnected powerlines cumulated over all the timesteps : {nb_real_disc}')



actions_count = {}
for act in li_actions:
    act_as_vect = tuple(act.to_vect())
    if not act_as_vect in actions_count:
        actions_count[act_as_vect] = 0
    actions_count[act_as_vect] += 1
print("The agent did {} different valid actions.".format(len(actions_count)))

for act in li_actions:
    print(act)
