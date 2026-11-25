"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import numpy as np
import andes
from matplotlib import pyplot as plt

andes.config_logger(stream_level=20)

ss = andes.load(andes.get_case('ieee14/ieee14.json'))
ss.PFlow.run()

ss.CPF.run(load_scale=2.0)

print(ss.CPF.max_lam)

fig, ax = ss.CPF.plot(bus_idx=14, show=False)
plt.show()

lam = ss.CPF.lam
nose = np.argmax(lam)

# Weakest bus = largest voltage drop from base to nose.
weak = np.argmax(ss.CPF.V[:, 0] - ss.CPF.V[:, nose])

fig, ax = plt.subplots()
ax.plot(lam, ss.CPF.V[weak, :], 'k-', linewidth=1.2)
ax.plot(lam[nose], ss.CPF.V[weak, nose], 'r*', markersize=10)
ax.set_xlabel(r'$\lambda$')
ax.set_ylabel(f'|V| at Bus {ss.Bus.idx.v[weak]} (pu)')
ax.grid(True, alpha=0.3)
fig.tight_layout()
plt.show()