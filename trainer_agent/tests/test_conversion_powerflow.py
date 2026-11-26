"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Validates `opf._pypowsybl_to_pandapower` against pypowsybl's own load flow.

The headline tests compare per-line active power on the Nordic network: small,
no phase shifters, no batteries, no HVDC. With the pre-balancing step applied
the DC flows must agree to floating-point precision, which makes this a tight
guard against any change in the branch model.

Each `test_regression_*` test pins one bug found while getting the conversion to
agree with pypowsybl - see the docstrings for what the symptom was.

Run:
    pytest trainer_agent/tests/test_conversion_powerflow.py -v
"""

import numpy as np
import pandapower as pp
import pytest

import powerflow_reference as ref

# Measured at the time of writing.
#   Nordic DC   max 3.4e-12 MW
#   Nordic AC   max 8.7e-03 MW
NORDIC_DC_MAX_MW = 1e-6
NORDIC_AC_MAX_MW = 0.05


# --------------------------------------------------------------------------
# Headline accuracy
# --------------------------------------------------------------------------


def test_nordic_dc_matches_pypowsybl(nordic_path):
    """Pre-balanced DC must agree to floating point on a network this simple."""
    _, diffs = ref.run_dc_comparison(nordic_path)
    stats = ref.summarise(diffs)

    assert stats["n_lines"] > 0, "no lines matched between the two models"
    assert stats["max_abs"] < NORDIC_DC_MAX_MW, (
        f"Nordic DC diverged from pypowsybl: {stats}\n"
        + diffs.sort_values("diff", key=abs, ascending=False).head(10).to_string()
    )


def test_nordic_ac_matches_pypowsybl(nordic_path):
    """AC against the stored snapshot; looser than DC since losses are modelled."""
    _, diffs = ref.run_ac_comparison(nordic_path)
    stats = ref.summarise(diffs)

    assert stats["n_lines"] > 0
    assert stats["max_abs"] < NORDIC_AC_MAX_MW, (
        f"Nordic AC diverged from pypowsybl: {stats}\n"
        + diffs.sort_values("diff", key=abs, ascending=False).head(10).to_string()
    )


def test_nordic_prebalance_removes_generation_load_gap(nordic_network):
    """The pre-balance is what makes the DC comparison reference-bus-insensitive.

    Without it the generation/load gap (the real transmission losses, ~450 MW
    on Nordic) is dumped entirely on whichever bus is slack, and pandapower and
    pypowsybl pick different ones - so flows differ by 100+ MW for reasons that
    have nothing to do with the conversion being right or wrong.
    """
    gen_before, load_before = ref.power_balance(nordic_network)
    assert abs(gen_before - load_before) > 100.0, (
        "expected a substantial loss-driven gap before balancing, got "
        f"{gen_before - load_before:.3f} MW"
    )

    ref.prebalance_dc(nordic_network)

    gen_after, load_after = ref.power_balance(nordic_network)
    assert abs(gen_after - load_after) < 1e-6, (
        f"pre-balance left a {gen_after - load_after:.3e} MW gap"
    )


# --------------------------------------------------------------------------
# Regressions: one test per bug found
# --------------------------------------------------------------------------


def test_regression_ratio_tap_changers_are_read(nordic_network):
    """Tap ratios must actually be populated.

    pypowsybl renamed this column from `tap_position` to `tap`. The old lookup
    sat inside a blanket ``except Exception: pass``, so it raised KeyError on
    every network and silently left *every* transformer at rho=1.0 - all 50 tap
    changers on Nordic were being ignored with no error surfaced anywhere.
    """
    rtc = nordic_network.get_ratio_tap_changers()
    assert len(rtc) > 0, "Nordic should have ratio tap changers"
    assert "tap" in rtc.columns, (
        f"expected a 'tap' column, got {rtc.columns.tolist()}"
    )

    steps = nordic_network.get_ratio_tap_changer_steps()
    resolved = [
        float(steps.loc[(tid, int(pos)), "rho"]) for tid, pos in rtc["tap"].items()
    ]
    assert len(resolved) == len(rtc), "some tap positions did not resolve to a step"
    assert any(r != 1.0 for r in resolved), (
        "no non-unity tap ratio resolved - the lookup is silently falling back"
    )


def test_regression_tap_ratio_applied_to_hv_side(nordic_network):
    """rho must go on vn_hv_kv, not vn_lv_kv.

    pandapower reuses vn_lv_kv as the impedance base when converting
    vk_percent back to ohms. Folding the tap ratio into vn_lv_kv therefore
    rescaled every tapped transformer's reactance by rho**2 (up to ~15% here),
    which showed up as a small, widely-spread flow error that was easy to
    mistake for numerical noise. vn_hv_kv is not used as an impedance base.
    """
    pp_net = ref.convert(nordic_network)
    source = nordic_network.get_2_windings_transformers().reindex(
        pp_net.trafo["name"].values
    )

    # LV side must be passed through untouched.
    np.testing.assert_allclose(
        pp_net.trafo["vn_lv_kv"].values, source["rated_u2"].values, rtol=1e-12
    )
    # HV side must be scaled, i.e. differ from rated_u1 for tapped units.
    scaled = ~np.isclose(pp_net.trafo["vn_hv_kv"].values, source["rated_u1"].values)
    assert scaled.any(), "no transformer had its HV rating adjusted by a tap ratio"


def test_regression_generator_setpoints_from_target_v(nordic_network):
    """vm_pu must come from target_v, not be hardcoded to 1.0.

    Nordic's real setpoints span 0.999-1.068 pu. Forcing every generator to a
    flat 1.0 pu is infeasible and Newton-Raphson simply failed to converge.
    """
    pp_net = ref.convert(nordic_network)

    assert not np.allclose(pp_net.gen["vm_pu"].values, 1.0), (
        "all generator setpoints are 1.0 pu - target_v is being ignored"
    )
    assert pp_net.gen["vm_pu"].between(0.8, 1.2).all(), (
        "generator setpoints outside a plausible range:\n"
        + pp_net.gen.loc[
            ~pp_net.gen["vm_pu"].between(0.8, 1.2), ["name", "vm_pu"]
        ].to_string()
    )

    # And the AC solve must actually converge, which is what the bug broke.
    pp.runpp(pp_net)
    assert pp_net["converged"]
