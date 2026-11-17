"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import matplotlib
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt 

matplotlib.rcParams.update({'font.size': 22})

results = []
for i in range(16):
    results.append(pd.read_csv(f"trainer_agent/case_118_ok/scenarios{i}.csv"))

results = pd.concat(results)
# pd.read_csv("contingencies")
# print(np.sum(results["init_v_PI"] != 0))
to_plot = []
res_to_plot = results[::]
min_difficulty = res_to_plot["difficulty"].min()
max_difficulty = res_to_plot["difficulty"].max()
labels = [-1] + list(range(1, max_difficulty+1))

print("corr:", np.corrcoef(res_to_plot["difficulty"], res_to_plot["overflow_PI"]))
for difficulty in labels:
    to_plot.append(res_to_plot["overflow_PI"][res_to_plot["difficulty"] == difficulty])
    # indices = np.logical_and(ratio_smart <= i / 10, ratio_smart > (i - 1) / 10)
    # if np.sum(indices) > 0:
    #     to_plot_errors.append(errors[indices])
    #     labels.append(f"]{(i - 1) / 10:.2},{i/10:.2}]")

plt.boxplot(to_plot, tick_labels=labels, whis=(0.1, 99.9))
plt.violinplot(to_plot, showextrema=False)
plt.xlabel("Difficulty")
plt.ylabel("Overflow PI")
plt.figure()

n_diff = max_difficulty
plt.hist(results["difficulty"], log=True, bins=n_diff, range=(0.5, n_diff + 0.5), label=np.arange(1, n_diff + 1))
plt.xlim(0, n_diff+1)
plt.xlabel("Difficulty")
plt.ylabel("Occurence")
plt.show()
print()