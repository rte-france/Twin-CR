"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
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