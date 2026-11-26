"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Validates the PTDF shortcut of `DCSensitivityFactors.iter_trip_flows` (behind
`get_problematic_gen_and_bridges_trips`) against pandapower.

For random generator trips and random bridge outages, the branch flows predicted
from the base-case DC model are compared with the reference procedure:

    apply the event on a copy of the net -> rundcpp -> opf.fcr -> set the gens to
    the FCR dispatch -> rundcpp -> read the branch flows.

For a bridge or an islanding N-2 pair, the pandapower reference drops the islanded generators (their
res_gen is NaN once the bus is cut off) before running FCR, which is what the
model assumes: the cut-off side vanishes and its net injection is lost.

Run:
    pytest trainer_agent/tests/test_lodf_trips.py -v
"""

import copy

import numpy as np
import pandapower as pp
import pytest
from pandapower.pypower.idx_brch import PF

import opf
import dc_sensitivity_factors
import powerflow_reference as ref

N_SAMPLES = 10
SEED = 0
TOL_MW = 1e-6


@pytest.fixture(scope="module")
def trips_setup(request):
    """Nordic converted to pandapower, its DC model and every predicted event."""
    if not ref.NORDIC_IIDM.exists():
        pytest.skip(f"Nordic network not available at {ref.NORDIC_IIDM}")
    import pypowsybl as ps

    psn = ps.network.load(str(ref.NORDIC_IIDM))
    ref.prebalance_dc(psn)
    net = ref.convert(psn)
    model = dc_sensitivity_factors.DCSensitivityFactors(net)
    events = {(is_bridge, key): (name, flows, ignored)
              for is_bridge, name, key, flows, ignored
              in model.iter_trip_flows(island_pairs=model.screen_n2()[1])}
    return net, model, events


def _branch_flows(net, model):
    return net._ppc["branch"][model.ppc_branch_rows, PF].real


def _fcr_flows(net, model):
    """Flows after FCR on an already-disturbed net."""
    net.gen["p_mw"] = opf.fcr(net)
    pp.rundcpp(net)
    return _branch_flows(net, model)


def _reference_gen_trip(net, model, gen_idx):
    net2 = copy.deepcopy(net)
    net2.gen.at[gen_idx, "in_service"] = False
    return _fcr_flows(net2, model)


def _reference_bridge(net, model, branches):
    """Bridge (int) or islanding N-2 pair (tuple of two ints) outage."""
    net2 = copy.deepcopy(net)
    for branch in np.atleast_1d(branches):
        typ, idx = model.branches.iloc[branch][["type", "index"]]
        net2[typ].at[idx, "in_service"] = False
    pp.rundcpp(net2)
    cut_off = net2.res_gen["p_mw"].isna()                   # gens on the islanded side
    net2.gen.loc[cut_off, "in_service"] = False
    pp.rundcpp(net2)
    return _fcr_flows(net2, model)


def _sample(events, kind):
    """Random event keys of one kind: 'gen', 'bridge' or 'pair' (islanding N-2)."""
    keys = sorted(k for is_bridge, k in events
                  if (kind == "gen") != is_bridge and (kind != "pair" or isinstance(k, tuple))
                  and (kind != "bridge" or not isinstance(k, tuple)))
    if not keys:
        pytest.skip(f"no {kind} events on this network")
    rng = np.random.default_rng(SEED)
    return [keys[i] for i in rng.choice(len(keys), size=min(N_SAMPLES, len(keys)), replace=False)]


def _assert_close(name, predicted, reference, ignored):
    ok = ~ignored & np.isfinite(reference)
    assert ok.any(), f"{name}: no branch left to compare"
    err = np.abs(predicted[ok] - reference[ok])
    assert err.max() < TOL_MW, f"{name}: max flow error {err.max():.3e} MW"


def test_gen_trips_match_pandapower(trips_setup):
    net, model, events = trips_setup
    for key in _sample(events, "gen"):
        name, flows, ignored = events[(False, key)]
        _assert_close(f"gen {name}", flows, _reference_gen_trip(net, model, key), ignored)


def test_bridge_outages_match_pandapower(trips_setup):
    net, model, events = trips_setup
    for key in _sample(events, "bridge"):
        name, flows, ignored = events[(True, key)]
        _assert_close(f"bridge {name}", flows, _reference_bridge(net, model, key), ignored)


def test_n2_islanding_pairs_match_pandapower(trips_setup):
    net, model, events = trips_setup
    for key in _sample(events, "pair"):
        name, flows, ignored = events[(True, key)]
        _assert_close(f"pair {name}", flows, _reference_bridge(net, model, key), ignored)
