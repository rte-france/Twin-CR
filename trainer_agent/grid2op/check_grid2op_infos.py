"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import pandas as pd

from matplotlib import pyplot as plt

infos = pd.read_csv("trainer_agent/infos.csv")
infos.iloc[infos["prod"].argmax()]
december_045 = infos[infos["chronic"] == "Scenario_december_045"]
december_045[["load", "prod"]].plot()
plt.show()
print()
# infos[["load", "prod"]].plot()
# plt.show()