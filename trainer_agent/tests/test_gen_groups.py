"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the TwinEU-core project.

Validates `DCSensitivityFactors.gen_group_overloads` and `gen_group_margins` (PTDF + FCR
model of an output change in a group of generators) against pandapower.

The reference procedure for a change of `fraction` of the output of the gens of a group is:

    scale the p_mw of the gens of the group on a copy of the net (an increase is capped at
    max_p_mw, as in contingency_finder.gen_contingency) -> opf.fcr -> set the gens to the FCR
    dispatch -> rundcpp -> read the branch flows.

The gens of the groups have no governor_kgover (like wind and solar), so they do not take part
in the FCR, which the model requires. The other gens get one.

Run:
    pytest trainer_agent/tests/test_gen_groups.py -v
"""

import copy

import numpy as np
import pandapower as pp
import pytest
from pandapower.pypower.idx_brch import PF

import opf
import dc_sensitivity_factors
import powerflow_reference as ref

N_GROUPS = 4
SEED = 0
TOL_FRACTION = 1e-3            # relative distance to the critical fraction where the reference is checked
SEARCH_LIMIT = 5.0             # an increase that never overloads below this fraction is reported as inf


@pytest.fixture(scope="module")
def groups_setup():
    """Nordic converted to pandapower, its DC model and random groups of non participating gens."""
    if not ref.NORDIC_IIDM.exists():
        pytest.skip(f"Nordic network not available at {ref.NORDIC_IIDM}")
    import pypowsybl as ps

    psn = ps.network.load(str(ref.NORDIC_IIDM))
    ref.prebalance_dc(psn)
    net = ref.convert(psn)

    gens = net.gen
    eligible = gens.index[gens["in_service"] & ~gens["slack"] & ~np.isclose(gens["p_mw"], 0)].to_numpy()
    rng = np.random.default_rng(SEED)
    cluster_gens = rng.permutation(eligible)[:len(eligible) // 2]       # the other half keeps the FCR going
    gens["governor_kgover"] = gens["max_p_mw"].clip(lower=0)
    gens.loc[cluster_gens, "governor_kgover"] = np.nan
    # Nordic gens have a lot of room: give the group gens caps within the range of the tested changes, one being
    # already at its max, so that the max_p_mw caps of an increase are exercised
    room = rng.uniform(0.05, 1.5, len(cluster_gens))
    room[0] = 0.0
    p_mw = gens.loc[cluster_gens, "p_mw"]
    gens.loc[cluster_gens, "max_p_mw"] = p_mw + p_mw.abs() * room
    groups = {f"group{i}": chunk for i, chunk in enumerate(np.array_split(cluster_gens, N_GROUPS))}
    groups["all"] = cluster_gens

    model = dc_sensitivity_factors.DCSensitivityFactors(net)
    return net, model, groups


def _reference_flows(net, model, gen_index, fraction):
    """Branch flows once the gens are multiplied by 1 + fraction and the FCR has run."""
    net2 = copy.deepcopy(net)
    net2.gen.loc[gen_index, "p_mw"] *= 1 + fraction
    if fraction > 0:
        net2.gen.loc[gen_index, "p_mw"] = np.minimum(net2.gen.loc[gen_index, "p_mw"],
                                                     net2.gen.loc[gen_index, "max_p_mw"])
    net2.gen["p_mw"] = opf.fcr(net2)
    pp.rundcpp(net2)
    return net2._ppc["branch"][model.ppc_branch_rows, PF].real


def _overloaded(model, flows, base_overloaded):
    """Names of the monitored branches over their rating, apart from the ones over it at the base case."""
    rating_mw = np.asarray(model.rating_mw, float)
    over = np.isfinite(rating_mw) & (np.abs(flows) > rating_mw) & ~base_overloaded
    return set(model.branches.index[over])


def _base_overloaded(net, model, groups):
    """Branches over their rating with no change (after FCR): ignored by default."""
    flows = _reference_flows(net, model, next(iter(groups.values())), 0.0)
    rating_mw = np.asarray(model.rating_mw, float)
    return np.isfinite(rating_mw) & (np.abs(flows) > rating_mw)


def test_margins_match_pandapower(groups_setup):
    net, model, groups = groups_setup
    base_overloaded = _base_overloaded(net, model, groups)
    n_checked = 0
    for direction in (1, -1):
        margins = model.gen_group_margins(groups, direction=direction)
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
        for critical in model.gen_group_margins(groups, direction=direction)["critical_percent"]:
            if np.isfinite(critical):
                fractions |= {critical / 100 * 0.9, critical / 100 * 1.1}
    n_overloaded = 0
    for fraction in sorted(f for f in fractions if f > -1):
        predicted = model.gen_group_overloads(groups, fraction)
        for name, gen_index in groups.items():
            reference = _overloaded(model, _reference_flows(net, model, gen_index, fraction), base_overloaded)
            assert set(predicted.get(name, {})) == reference, f"{name}, fraction {fraction:+.2%}"
            n_overloaded += bool(reference)
    assert n_overloaded, "nothing overloads on this network: the test checks nothing"


def test_participating_gens_are_rejected(groups_setup):
    """The headroom of a gen that shares the FCR would change with the group's change: not modelled."""
    net, model, groups = groups_setup
    gens = net.gen
    participating = gens.index[(gens["governor_kgover"] > 0) & ~gens["slack"] & gens["in_service"]
                               & ~np.isclose(gens["p_mw"], 0)].to_numpy()[:1]
    with pytest.raises(NotImplementedError):
        model.gen_group_margins({"participating": participating})
