"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Checks of `pypowsybl_to_andes.pypowsybl_to_andes` against pypowsybl's own AC load flow: bus voltages/angles,
branch flows (lines and transformers) and total losses.

Not collected by pytest on its own (no `test_` prefix). A test module for one network does

    from andes_conversion_checks import *  # noqa: F401,F403

and defines a module-scoped `network_path` fixture (skipping when the file is missing). It may also override the
module-scoped `conversion_tolerances` fixture to loosen the defaults below.
"""

import andes
import pypowsybl as ps
import pytest

import check_pypowsybl_to_andes as check
from pypowsybl_to_andes import pypowsybl_to_andes

__all__ = [
    "conversion_tolerances",
    "converted_network",
    "test_andes_power_flow_converges",
    "test_bus_voltages_match_pypowsybl",
    "test_branch_flows_match_pypowsybl",
    "test_total_losses_match_pypowsybl",
]

DEFAULT_TOLERANCES = {
    "voltage_pu": 1e-3,
    "angle_deg": 0.05,
    "flow_mw": 0.5,
    "flow_mvar": 0.5,
    "losses_mw": 1.0,
}


@pytest.fixture(scope="module")
def conversion_tolerances():
    return DEFAULT_TOLERANCES


@pytest.fixture(scope="module")
def converted_network(network_path):
    """(pypowsybl network, solved ANDES system, pypowsybl slack mismatch in MW)."""
    network = ps.network.load(str(network_path))
    reference_bus_id, slack_mismatch_mw = check.run_pypowsybl_reference(network, use_reactive_limits=True)
    andes_system = pypowsybl_to_andes(network, slack_bus_id=reference_bus_id)
    andes.config_logger(stream_level=30)
    andes_system.PFlow.run()
    return network, andes_system, slack_mismatch_mw


def test_andes_power_flow_converges(converted_network):
    _, andes_system, _ = converted_network
    assert andes_system.PFlow.converged


def test_bus_voltages_match_pypowsybl(converted_network, conversion_tolerances):
    network, andes_system, _ = converted_network
    compared = check.compare_bus_voltages(network, andes_system)

    assert len(compared) > 0, "no buses matched between the two models"
    assert compared["voltage_error_pu"].max() < conversion_tolerances["voltage_pu"]
    assert compared["angle_error_deg"].max() < conversion_tolerances["angle_deg"]


@pytest.mark.parametrize("branch_type", ["lines", "transformers"])
def test_branch_flows_match_pypowsybl(converted_network, conversion_tolerances, branch_type):
    network, andes_system, _ = converted_network
    compared = check.compare_branch_flows(network, andes_system)[branch_type]

    assert len(compared) > 0, f"no {branch_type} matched between the two models"
    assert compared["p_error_mw"].max() < conversion_tolerances["flow_mw"]
    assert compared["q_error_mvar"].max() < conversion_tolerances["flow_mvar"]


def test_total_losses_match_pypowsybl(converted_network, conversion_tolerances):
    network, andes_system, slack_mismatch_mw = converted_network
    pypowsybl_losses_mw, andes_losses_mw = check.compare_losses(network, andes_system, slack_mismatch_mw)

    assert abs(andes_losses_mw - pypowsybl_losses_mw) < conversion_tolerances["losses_mw"]
