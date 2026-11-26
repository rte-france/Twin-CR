"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Validates `DCSensitivityFactors.load_group_overloads` and `load_group_margins` (PTDF + FCR
model of a load change in a group of loads) against pandapower.

The reference procedure for a change of `fraction` of the loads of a group is:

    scale the p_mw of the loads of the group on a copy of the net -> opf.fcr -> set the gens to
    the FCR dispatch -> rundcpp -> read the branch flows.

load_group_overloads must report exactly the branches that this reference overloads, and
load_group_margins must return the fraction at which the reference starts to overload: nothing
overloaded just below it, the limiting branch overloaded just above it.

Run:
    pytest trainer_agent/tests/test_load_groups.py -v
"""

import copy

import numpy as np
import pandapower as pp
import pytest
from pandapower.pypower.idx_brch import PF

import opf
import dc_sensitivity_factors
import powerflow_reference as ref

N_GROUPS = 5
SEED = 0
TOL_FRACTION = 1e-3            # relative distance to the critical fraction where the reference is checked
SEARCH_LIMIT = 5.0             # an increase that never overloads below this fraction is reported as inf


@pytest.fixture(scope="module")
def groups_setup():
    """Nordic converted to pandapower, its DC model and random groups of loads."""
    if not ref.NORDIC_IIDM.exists():
        pytest.skip(f"Nordic network not available at {ref.NORDIC_IIDM}")
    import pypowsybl as ps

    psn = ps.network.load(str(ref.NORDIC_IIDM))
    ref.prebalance_dc(psn)
    net = ref.convert(psn)
    model = dc_sensitivity_factors.DCSensitivityFactors(net)

    rng = np.random.default_rng(SEED)
    shuffled = rng.permutation(net.load.index.to_numpy())
    groups = {f"group{i}": chunk for i, chunk in enumerate(np.array_split(shuffled, N_GROUPS))}
    groups["all"] = net.load.index.to_numpy()
    return net, model, groups


def _reference_flows(net, model, load_index, fraction):
    """Branch flows once the loads are multiplied by 1 + fraction and the FCR has run."""
    net2 = copy.deepcopy(net)
    net2.load.loc[load_index, "p_mw"] *= 1 + fraction
    net2.gen["p_mw"] = opf.fcr(net2)
    pp.rundcpp(net2)
    return net2._ppc["branch"][model.ppc_branch_rows, PF].real


def _overloaded(model, flows, base_overloaded):
    """Names of the monitored branches over their rating, apart from the ones over it at the base case."""
    rating_mw = np.asarray(model.rating_mw, float)
    over = np.isfinite(rating_mw) & (np.abs(flows) > rating_mw) & ~base_overloaded
    return set(model.branches.index[over])


def _base_overloaded(net, model, groups):
    """Branches over their rating with no load change (after FCR): ignored by default."""
    flows = _reference_flows(net, model, next(iter(groups.values())), 0.0)
    return np.isfinite(np.asarray(model.rating_mw, float)) & (np.abs(flows) > np.asarray(model.rating_mw, float))


def test_margins_match_pandapower(groups_setup):
    net, model, groups = groups_setup
    base_overloaded = _base_overloaded(net, model, groups)
    n_checked = 0
    for direction in (1, -1):
        margins = model.load_group_margins(groups, direction=direction)
        for name, row in margins.iterrows():
            critical = abs(row["critical_percent"]) / 100
            if not np.isfinite(critical):
                # nothing overloads over the whole search range
                limit = SEARCH_LIMIT if direction > 0 else 1.0
                flows = _reference_flows(net, model, groups[name], direction * limit * (1 - 1e-6))
                assert not _overloaded(model, flows, base_overloaded), f"{name}, direction {direction}: inf margin but overload"
                continue
            n_checked += 1
            below = _reference_flows(net, model, groups[name], direction * critical * (1 - TOL_FRACTION))
            above = _reference_flows(net, model, groups[name], direction * critical * (1 + TOL_FRACTION))
            assert not _overloaded(model, below, base_overloaded), \
                f"{name}, direction {direction}: overload before the critical {critical:.4%}"
            assert row["limiting_branch"] in _overloaded(model, above, base_overloaded), \
                f"{name}, direction {direction}: {row['limiting_branch']} not overloaded after the critical {critical:.4%}"
    assert n_checked, "no group with a finite margin on this network: the test checks nothing"


def test_overloads_match_pandapower(groups_setup):
    net, model, groups = groups_setup
    base_overloaded = _base_overloaded(net, model, groups)
    # fixed changes, plus ones around the critical fractions so that both outcomes are covered
    fractions = {-0.5, 0.3, 1.0}
    for direction in (1, -1):
        for critical in model.load_group_margins(groups, direction=direction)["critical_percent"]:
            if np.isfinite(critical):
                fractions |= {critical / 100 * 0.9, critical / 100 * 1.1}
    n_overloaded = 0
    for fraction in sorted(f for f in fractions if f > -1):
        predicted = model.load_group_overloads(groups, fraction)
        for name, load_index in groups.items():
            reference = _overloaded(model, _reference_flows(net, model, load_index, fraction), base_overloaded)
            assert set(predicted.get(name, {})) == reference, f"{name}, fraction {fraction:+.2%}"
            n_overloaded += bool(reference)
    assert n_overloaded, "nothing overloads on this network: the test checks nothing"
