"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
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