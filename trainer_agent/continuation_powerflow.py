"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import andes
import numpy as np
import pypowsybl as ps

from matplotlib import pyplot as plt

from fast_cpf import install_fast_cpf
from pypowsybl_to_andes import pypowsybl_to_andes


def continuation_powerflow(net, plot=False):
    andes.config_logger(stream_level=20)

    # ss = andes.load(andes.get_case('ieee14/ieee14.json'))
    ss = pypowsybl_to_andes(net)
    ss.PFlow.run()

    install_fast_cpf(ss)  # factorize only the sparse Jacobian instead of the bordered one (~9x faster)
    ss.CPF.run(load_scale=2.0)

    if plot:
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

    return ss.CPF.max_lam


if __name__ == "__main__":
    net = ps.network.load("temp copy.xiidm")
    continuation_powerflow(net, True)
    
