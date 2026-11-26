"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

pypowsybl -> ANDES conversion checks on the Nordic network (see andes_conversion_checks.py).

Measured on Nordic: max |dV| 1e-5 pu, max |dAngle| 1.1e-3 deg, max |dP| 0.028 MW, max |dQ| 0.014 Mvar,
losses difference 0.0 MW; the default tolerances leave headroom above these.

Run:
    pytest trainer_agent/tests/test_pypowsybl_to_andes.py -v
"""

import pytest

import powerflow_reference as ref
from andes_conversion_checks import *  # noqa: F401,F403


@pytest.fixture(scope="module")
def network_path():
    if not ref.NORDIC_IIDM.exists():
        pytest.skip(f"Nordic network not available at {ref.NORDIC_IIDM}")
    return ref.NORDIC_IIDM
