"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import numpy as np
from matplotlib import pyplot as plt
plt.rcParams.update({'font.size': 14})
plt.rcParams.update({'lines.linewidth': 2})

x = np.arange(-30, 30)
abs = abs(x)
squared = x ** 2

capped = np.minimum(abs, 10)

plt.plot(x, capped)
plt.xlabel("P redispatch (MW)")
plt.ylabel("Cost (€)")
plt.ylim((-1, 17))
plt.show()