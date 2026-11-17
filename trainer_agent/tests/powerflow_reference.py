"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the TwinEU-core project.

Reference harness for validating `opf._pypowsybl_to_pandapower` against
pypowsybl's own load flow.

The point of comparison is per-line active power: pandapower's
``res_line.p_from_mw`` versus pypowsybl's ``get_lines()["p1"]``. Both use the
same sign convention (positive = flowing into the line at side 1 / the "from"
bus), so they are directly comparable once matched by element name.

Why the pre-balancing step matters
----------------------------------
DC load flow ignores resistive losses, so a network whose generation exceeds
its load by the real transmission losses (~450 MW on Nordic, more on larger networks)
carries a phantom surplus in DC. That surplus has to be absorbed somewhere,
and it all lands on whichever bus is the reference/slack. pandapower and
pypowsybl pick different reference buses, so comparing their raw DC output is
meaningless - flows differ by 100+ MW purely from where the surplus was parked.

`prebalance_dc` replicates what `ContingencyFinder.update_network` does before
converting (trainer_agent/contingency_finder.py): it pins generator target_p /
load p0 to the solved AC state and re-solves DC with
``balance_type=PROPORTIONAL_TO_LOAD``, which spreads the mismatch across loads.
Generation then equals load to ~1e-9 MW, there is nothing left for the slack to
absorb, and the DC comparison becomes reference-bus-insensitive - which is what
makes an exact-match assertion meaningful.

Run standalone for an ad-hoc report:

    python trainer_agent/tests/powerflow_reference.py                      # Nordic
    python trainer_agent/tests/powerflow_reference.py --iidm path/to/net.iidm
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pandapower as pp
import pypowsybl as ps

REPO_ROOT = Path(__file__).resolve().parents[2]

NORDIC_IIDM = REPO_ROOT / "docs/orchestrator/examples/Nordic/Nordic.iidm"


def prebalance_dc(psn):
    """Pin injections to the solved state and re-solve DC, balancing on loads.

    Mirrors ContingencyFinder.update_network (trainer_agent/contingency_finder.py).
    MUTATES `psn` in place and leaves pypowsybl's DC solution stored on it, so
    call `read_pypowsybl_line_flows(psn)` afterwards to capture the reference.
    """
    generators = psn.get_generators()
    generators["target_p"] = -generators["p"]
    psn.update_generators(generators[["target_p"]])

    loads = psn.get_loads()
    loads["p0"] = loads["p"]
    psn.update_loads(loads[["p0"]])

    params = ps.loadflow.Parameters(
        balance_type=ps.loadflow.BalanceType.PROPORTIONAL_TO_LOAD
    )
    return ps.loadflow.run_dc(psn, params)


def power_balance(psn):
    """(total generation, total load) in MW, for asserting the pre-balance worked."""
    return -psn.get_generators()["p"].sum(), psn.get_loads()["p"].sum()


def read_pypowsybl_line_flows(psn):
    """Reference side-1 active power per line, as currently stored on the network.

    Read this straight after a run_ac/run_dc call - `get_lines()` returns the
    stored solution, and any later solve overwrites it.
    """
    return psn.get_lines()[["p1"]].copy()


def set_slack(pp_net, preferred=None):
    """Mark the slack generator the way opf.powsybl2pandapower does.

    `preferred` is the name of the generator to use as slack; when None or absent
    from the network, the first generator row is used.
    """
    pp_net.gen["slack"] = False
    mask = pp_net.gen["name"] == preferred
    if mask.any():
        pp_net.gen.loc[mask, "slack"] = True
    else:
        pp_net.gen.iloc[0, pp_net.gen.columns.get_loc("slack")] = True
    return pp_net.gen.loc[pp_net.gen["slack"], "name"].iloc[0]


def convert(psn, preferred_slack=None):
    """Convert to pandapower and designate the slack, without solving."""
    from opf import _pypowsybl_to_pandapower

    pp_net = _pypowsybl_to_pandapower(psn)
    set_slack(pp_net, preferred_slack)
    return pp_net


def compare_line_flows(pp_net, reference, exclude=()):
    """Join pandapower line flows onto the pypowsybl reference, matched by name.

    Returns a frame indexed by line name with columns p_pandapower, p_pypowsybl
    and diff (pandapower - pypowsybl), restricted to lines present in both.
    """
    got = pp_net.res_line[["p_from_mw"]].copy()
    got["name"] = pp_net.line["name"].values
    got = got.set_index("name").rename(columns={"p_from_mw": "p_pandapower"})

    out = got.join(reference.rename(columns={"p1": "p_pypowsybl"}), how="inner")
    out = out.dropna(subset=["p_pandapower", "p_pypowsybl"])
    out["diff"] = out["p_pandapower"] - out["p_pypowsybl"]

    drop = [name for name in exclude if name in out.index]
    if drop:
        out = out.drop(index=drop)
    return out


def summarise(diffs):
    """Headline accuracy figures for a compare_line_flows result."""
    err = diffs["diff"].abs()
    return {
        "n_lines": int(len(diffs)),
        "max_abs": float(err.max()) if len(err) else 0.0,
        "mean_abs": float(err.mean()) if len(err) else 0.0,
        "median_abs": float(err.median()) if len(err) else 0.0,
        "sum_abs": float(err.sum()),
        "n_over_1mw": int((err > 1.0).sum()),
        "n_over_10mw": int((err > 10.0).sum()),
    }


def run_dc_comparison(iidm_path, exclude=(), preferred_slack=None):
    """Full DC pipeline: load -> pre-balance -> convert -> rundcpp -> compare."""
    psn = ps.network.load(str(iidm_path))
    prebalance_dc(psn)
    reference = read_pypowsybl_line_flows(psn)

    pp_net = convert(psn, preferred_slack)
    pp.rundcpp(pp_net)

    return pp_net, compare_line_flows(pp_net, reference, exclude=exclude)


def run_ac_comparison(iidm_path, exclude=(), preferred_slack=None):
    """AC pipeline against the solution already stored in the IIDM file.

    No pre-balancing here: the stored AC state is self-consistent (its
    generation/load gap *is* the physical losses), so the slack only has to
    absorb a near-zero residual and the choice of slack barely matters.
    """
    psn = ps.network.load(str(iidm_path))
    reference = read_pypowsybl_line_flows(psn)

    pp_net = convert(psn, preferred_slack)
    pp.runpp(pp_net)

    return pp_net, compare_line_flows(pp_net, reference, exclude=exclude)


def transformer_reactance_roundtrip(psn, pp_net):
    """Per-transformer reactance in ohms: IIDM input vs what pandapower rebuilt.

    pandapower stores transformer impedance as vk_percent/vkr_percent rather
    than ohms, and recovers reactance as
    ``x = sign(z) * sqrt(z**2 - r**2)`` (build_branch._calc_r_x_from_dataframe).
    An unsigned vk_percent therefore silently flips every negative-reactance
    transformer, so this reproduces pandapower's own reconstruction and
    compares it against the IIDM values it came from.
    """
    from pandapower.build_branch import _calc_r_x_from_dataframe

    trafo = pp_net.trafo
    vn_bus_lv = pp_net.bus["vn_kv"].reindex(trafo["lv_bus"].values).values
    vn_trafo_lv = trafo["vn_lv_kv"].values

    _, x_pu = _calc_r_x_from_dataframe(
        "pf", trafo, vn_bus_lv, vn_trafo_lv, pp_net.sn_mva
    )
    base_r = vn_bus_lv**2 / pp_net.sn_mva

    source = psn.get_2_windings_transformers().reindex(trafo["name"].values)
    out = pd.DataFrame(
        {
            "x_iidm": source["x"].values,
            "x_pandapower": x_pu * base_r,
        },
        index=trafo["name"].values,
    )
    out["diff"] = out["x_pandapower"] - out["x_iidm"]
    out["sign_ok"] = np.sign(out["x_pandapower"]) == np.sign(out["x_iidm"])
    return out


def bus_injection_mismatch(psn, pp_net):
    """Per-bus net active power injection: pypowsybl model vs pandapower results.

    DC flows are fully determined by injections and susceptances, so this
    separates the two classes of error: a nonzero entry here means an element
    is missing or mis-signed in the conversion, while all-zeros alongside
    mismatched flows points at branch impedance instead.

    Indexed by pypowsybl bus id. Positive = injection into the bus.
    """
    bus_name = pp_net.bus["name"]
    valid = set(bus_name.values)

    injected = pd.Series(0.0, index=sorted(valid))
    # IIDM terminal convention: p > 0 is consumption, so injection is -p.
    for getter, column in [
        ("get_generators", "p"),
        ("get_loads", "p"),
        ("get_shunt_compensators", "p"),
        ("get_batteries", "p"),
        ("get_vsc_converter_stations", "p"),
        ("get_lcc_converter_stations", "p"),
    ]:
        frame = getattr(psn, getter)()
        if not len(frame):
            continue
        frame = frame[frame["bus_id"].isin(valid)]
        if len(frame):
            injected = injected.add(
                -frame.groupby("bus_id")[column].sum(), fill_value=0.0
            )

    got = pd.Series(0.0, index=pp_net.bus.index)
    got = got.add(pp_net.res_gen.groupby(pp_net.gen["bus"])["p_mw"].sum(), fill_value=0.0)
    got = got.add(
        -pp_net.res_load.groupby(pp_net.load["bus"])["p_mw"].sum(), fill_value=0.0
    )
    if len(pp_net.sgen):
        got = got.add(
            pp_net.res_sgen.groupby(pp_net.sgen["bus"])["p_mw"].sum(), fill_value=0.0
        )
    if len(pp_net.shunt):
        got = got.add(
            -pp_net.res_shunt.groupby(pp_net.shunt["bus"])["p_mw"].sum(), fill_value=0.0
        )
    if len(pp_net.dcline):
        got = got.add(
            -pp_net.res_dcline.groupby(pp_net.dcline["from_bus"])["p_from_mw"].sum(),
            fill_value=0.0,
        )
        got = got.add(
            -pp_net.res_dcline.groupby(pp_net.dcline["to_bus"])["p_to_mw"].sum(),
            fill_value=0.0,
        )
    got.index = bus_name.reindex(got.index).values

    out = pd.DataFrame({"pypowsybl": injected, "pandapower": got}).fillna(0.0)
    out["diff"] = out["pandapower"] - out["pypowsybl"]
    return out


def converter_station_buses(psn):
    """Bus ids carrying an HVDC converter station.

    pandapower models an HVDC link as a single dcline with one combined
    ``loss_percent``, while pypowsybl applies each station's own ``loss_factor``
    at its own terminal. The two distribute converter losses slightly
    differently, so injections at these buses agree only to ~2 MW.
    """
    buses = set()
    for getter in ("get_vsc_converter_stations", "get_lcc_converter_stations"):
        frame = getattr(psn, getter)()
        if len(frame):
            buses |= set(frame["bus_id"].dropna())
    return buses


def slack_bus_names(pp_net):
    """Bus name(s) hosting the pandapower slack generator.

    The slack absorbs whatever residual the solve leaves over, so its injection
    is expected to differ from the pypowsybl reference by construction.
    """
    slack_buses = pp_net.gen.loc[pp_net.gen["slack"], "bus"].unique()
    return set(pp_net.bus["name"].reindex(slack_buses).dropna())


def report(label, iidm_path, exclude=(), preferred_slack=None):
    """Print an ad-hoc accuracy report (AC, DC, worst lines, transformer reactance)."""
    print(f"\n=== {label}: {iidm_path.name} ===")
    if not iidm_path.exists():
        print(f"  MISSING: {iidm_path}")
        return

    _, ac = run_ac_comparison(iidm_path, exclude, preferred_slack)
    print("AC  " + "  ".join(f"{k}={v}" for k, v in summarise(ac).items()))

    pp_net, dc = run_dc_comparison(iidm_path, exclude, preferred_slack)
    print("DC  " + "  ".join(f"{k}={v}" for k, v in summarise(dc).items()))

    print("\nTop 10 DC differences:")
    print(dc.sort_values("diff", key=abs, ascending=False).head(10).to_string())

    psn = ps.network.load(str(iidm_path))
    roundtrip = transformer_reactance_roundtrip(psn, pp_net)
    negative = roundtrip[roundtrip["x_iidm"] < 0]
    print(
        f"\nTransformer reactance: {len(negative)} negative-x of {len(roundtrip)}; "
        f"max abs error {roundtrip['diff'].abs().max():.3e} ohm; "
        f"sign agreement {int(roundtrip['sign_ok'].sum())}/{len(roundtrip)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iidm", type=Path, default=NORDIC_IIDM, help="network to report on (default: Nordic)")
    args = parser.parse_args()

    import sys

    sys.path.insert(0, str(REPO_ROOT / "trainer_agent"))
    pd.set_option("display.width", 250)

    report(args.iidm.stem, args.iidm)
