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
import re
from matplotlib import pyplot as plt 

overflow_PI = pd.read_csv("overflow_PI.csv")
overflow_PI = overflow_PI.set_index(["outage_1", "outage_2"])
contingencies = pd.read_csv("contingencies.csv")

outage_names = contingencies["id"].str.split(re.escape("_+_"), expand=True)
contingencies["outage_1"] = outage_names[0]
contingencies["outage_2"] = outage_names[1]
contingencies = contingencies.set_index(["outage_1", "outage_2"]).drop(columns="id")

overflow_PI = overflow_PI.join(contingencies)
overflow_PI = overflow_PI[overflow_PI["difficulty"] > 0]

to_plot = []
labels = np.unique(overflow_PI["difficulty_10"].values)

print("corr:", np.corrcoef(overflow_PI["difficulty_10"], overflow_PI["overload_index"]))
plt.scatter(overflow_PI["difficulty_10"], overflow_PI["overload_index"])
# for difficulty in labels:
#     to_plot.append(overflow_PI["overload_index"][overflow_PI["difficulty_10"] == difficulty].values)
#     # indices = np.logical_and(ratio_smart <= i / 10, ratio_smart > (i - 1) / 10)
#     # if np.sum(indices) > 0:
#     #     to_plot_errors.append(errors[indices])
#     #     labels.append(f"]{(i - 1) / 10:.2},{i/10:.2}]")

# plt.boxplot(to_plot, tick_labels=labels, whis=(0.1, 99.9))
# plt.violinplot(to_plot, showextrema=False)
# plt.xlabel("Difficulty")
# plt.ylabel("Overflow PI")
plt.show()