"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Check that a pypowsybl network survives the pypowsybl -> PSS/E RAW -> ANDES conversion.

Steps:
  1. Run an AC load flow in pypowsybl on the node-breaker network (reference solution).
  2. Convert a copy to bus-breaker topology (the PSS/E file of a node-breaker network is not usable by ANDES).
  3. Export it to PSS/E RAW (v35), rewrite the file so ANDES reads it correctly (see rewrite_raw_for_andes).
  4. Run the ANDES power flow on the main island.
  5. Compare: global balance, then bus voltages/angles.

This validates the PASSIVE network model (impedances, taps, shunts, topology). Generator voltage control, Q limits and
HVDC are deliberately pinned to the solved pypowsybl state, so they are NOT tested.

Usage:
    python check_psse_andes_conversion.py [network_file] [--keep-dir DIR]
"""

import argparse
import os
import re
import tempfile
from pathlib import Path

import andes
import numpy as np
import pandas as pd
import pypowsybl as ps

from dotenv import load_dotenv


load_dotenv()
DEFAULT_NETWORK_PATH = os.environ.get("IIDM_FILE")

VOLTAGE_TOLERANCE_PU = 1e-3
ANGLE_TOLERANCE_DEG = 0.1
MIN_FRACTION_OF_BUSES_WITHIN_TOLERANCE = 0.98
RAW_BUS_NAME_LENGTH = 12  # PSS/E bus names are limited to 12 characters


PYPOWSYBL_LOAD_FLOW_PARAMETERS = ps.loadflow.Parameters(
    distributed_slack=False,
    transformer_voltage_control_on=False,
    voltage_init_mode=ps.loadflow.VoltageInitMode.DC_VALUES,
)


def run_main_component_load_flow(network):
    """Single slack (like ANDES), no transformer voltage control, DC initialisation (the file holds no stored
    voltages and a flat start does not converge on this network)."""
    results = ps.loadflow.run_ac(network, PYPOWSYBL_LOAD_FLOW_PARAMETERS)
    main_result = next(result for result in results if result.synchronous_component_num == 0)
    print(
        f"[pypowsybl] main component status: {main_result.status.name} "
        f"(reference bus {main_result.reference_bus_id}, slack mismatch "
        f"{[round(slack.active_power_mismatch, 1) for slack in main_result.slack_bus_results]} MW)"
    )
    if main_result.status != ps.loadflow.ComponentStatus.CONVERGED:
        raise RuntimeError("pypowsybl AC load flow did not converge: cannot use it as reference")
    return sum(slack.active_power_mismatch for slack in main_result.slack_bus_results)


def make_busbar_section_regulation_local(network, solved_bus_voltages_kv: pd.Series) -> None:
    """
    Generators regulating the voltage of a busbar section cannot be exported to a bus-branch topology, and a
    regulated element can only be a busbar section or an injection. Make these generators regulate their own
    terminal, with the target set to the voltage their own bus has in the solved state (passed in, bus id -> kV):
    the solved state stays a solution, only the control topology is simplified.
    """
    generators = network.get_generators()
    generators_on_busbar_section = generators[
        generators["regulated_element_id"].isin(network.get_busbar_sections().index)
    ]
    if generators_on_busbar_section.empty:
        return

    own_bus_voltage_kv = solved_bus_voltages_kv.reindex(generators_on_busbar_section["bus_id"]).to_numpy()
    # Generators on buses outside the solved component keep their target (they play no role in the main component).
    target_v_kv = np.where(np.isnan(own_bus_voltage_kv), generators_on_busbar_section["target_v"], own_bus_voltage_kv)
    network.update_generators(
        id=list(generators_on_busbar_section.index),
        regulated_element_id=list(generators_on_busbar_section.index),
        target_v=target_v_kv,
    )
    print(f"[topology] {len(generators_on_busbar_section)} generators regulating a busbar section now regulate their own terminal")


def replace_vsc_stations_by_fixed_loads(network, solved_vsc_stations: pd.DataFrame) -> None:
    """
    ANDES ignores the VSC converter blocks of the RAW file, which would drop about 1.4 GW of HVDC injection on this
    network. Replace each HVDC line and its VSC stations by a fixed P/Q load at the AC terminal, using the values of
    the solved original network (load convention: positive = consumption). The solved state stays a solution.
    """
    stations = network.get_vsc_converter_stations(all_attributes=True)
    if stations.empty:
        return
    solved_values = solved_vsc_stations.reindex(stations.index)[["p", "q"]].fillna(0.0)
    hvdc_line_ids = list(network.get_hvdc_lines().index)
    network.remove_elements(hvdc_line_ids + list(stations.index))
    network.create_loads(
        id=[f"{station_id}_AS_LOAD" for station_id in stations.index],
        voltage_level_id=stations["voltage_level_id"].to_numpy(),
        bus_id=stations["bus_breaker_bus_id"].to_numpy(),
        p0=solved_values["p"].to_numpy(),
        q0=solved_values["q"].to_numpy(),
    )
    print(
        f"[topology] {len(stations)} VSC stations replaced by fixed loads "
        f"(net {solved_values['p'].sum():.1f} MW consumed)"
    )


def run_pypowsybl_reference(network_path: str):
    """
    Load the node-breaker network, solve it, convert it to bus-branch topology and check the converted network
    gives the same solution. The PSS/E file written by powsybl for a node-breaker network puts every voltage level
    on a single bus and keeps the real topology in substation blocks that ANDES does not read: that model is not
    equivalent to pypowsybl's (open couplers are ignored).
    """
    original_network = ps.network.load(network_path)
    run_main_component_load_flow(original_network)
    original_voltages = original_network.get_buses()["v_mag"]
    original_bus_breaker_voltages = original_network.get_bus_breaker_view_buses()["v_mag"]

    # Convert a freshly loaded copy: a network that went through a load flow also carries a slackTerminal
    # extension on a busbar section, which blocks the bus-branch export.
    network_to_convert = ps.network.load(network_path)
    make_busbar_section_regulation_local(network_to_convert, original_voltages)
    bus_branch_xml = network_to_convert.save_to_string(
        format="XIIDM", parameters={"iidm.export.xml.topology-level": "BUS_BREAKER"}
    )
    network = ps.network.load_from_string("bus_branch.xiidm", bus_branch_xml)
    replace_vsc_stations_by_fixed_loads(network, original_network.get_vsc_converter_stations())
    slack_mismatch_mw = run_main_component_load_flow(network)

    converted_voltages = network.get_bus_breaker_view_buses()["v_mag"]
    common_bus_ids = original_bus_breaker_voltages.dropna().index.intersection(converted_voltages.dropna().index)
    max_voltage_difference_kv = (
        original_bus_breaker_voltages.loc[common_bus_ids] - converted_voltages.loc[common_bus_ids]
    ).abs().max()
    print(
        f"[topology] bus-branch conversion: {len(network.get_buses())} buses; max |dV| vs node-breaker solution "
        f"on {len(common_bus_ids)} common buses = {max_voltage_difference_kv:.4f} kV"
    )
    return network, slack_mismatch_mw


def export_to_psse_raw(network, output_directory: Path) -> Path:
    raw_base_path = output_directory / "network_export"
    network.save(
        str(raw_base_path),
        format="PSS/E",
        parameters={"psse.export.raw-format": "true", "psse.export.update": "false"},
    )
    raw_candidates = sorted(output_directory.glob("network_export.raw"))
    if not raw_candidates:
        raise FileNotFoundError(
            f"No .raw file written in {output_directory}. Files: {[p.name for p in output_directory.iterdir()]}"
        )
    print(f"[export] files written: {[p.name for p in output_directory.iterdir()]}")
    return raw_candidates[0]


def collect_line_end_shunts(raw_lines: list[str], is_kept) -> dict[str, tuple[float, float]]:
    """
    Sum per bus number (pu on the system base) the passive shunts that ANDES's RAW reader ignores:
    the in-service branches' end shunts (GI, BI at the I end, GJ, BJ at the J end) and the in-service transformers'
    magnetizing conductance MAG1 (with CM=1, in pu on the system base, connected on the winding 1 bus).
    """
    first_column_after_rates = {"GI": 19, "BI": 20, "GJ": 21, "BJ": 22, "ST": 23}
    shunts: dict[str, list[float]] = {}
    current_block = ""
    line_index = 0
    while line_index < len(raw_lines):
        line = raw_lines[line_index]
        if line.startswith("0 /"):
            block_name = re.search(r"BEGIN (.*?) DATA", line)
            current_block = block_name.group(1) if block_name else ""
            line_index += 1
            continue
        fields = line.split(",")
        if current_block == "TRANSFORMER":
            record_line_count = 4 if int(fields[2]) == 0 else 5
            transformer_in_service = int(fields[11]) == 1
            magnetizing_code_is_pu = int(fields[6]) == 1
            if transformer_in_service and magnetizing_code_is_pu and is_kept(fields[0], fields[1]):
                accumulated = shunts.setdefault(fields[0].strip(), [0.0, 0.0])
                accumulated[0] += float(fields[7])
            line_index += record_line_count
            continue
        line_index += 1
        if current_block != "BRANCH":
            continue
        if int(fields[first_column_after_rates["ST"]]) != 1 or not is_kept(fields[0], fields[1]):
            continue
        for bus_field, conductance_key, susceptance_key in ((0, "GI", "BI"), (1, "GJ", "BJ")):
            conductance = float(fields[first_column_after_rates[conductance_key]])
            susceptance = float(fields[first_column_after_rates[susceptance_key]])
            if conductance or susceptance:
                accumulated = shunts.setdefault(fields[bus_field].strip(), [0.0, 0.0])
                accumulated[0] += conductance
                accumulated[1] += susceptance
    return {bus_number: (values[0], values[1]) for bus_number, values in shunts.items()}


def rewrite_raw_for_andes(raw_path: Path, kept_bus_numbers: set | None = None) -> Path:
    """
    Make the RAW file written by powsybl (v35) readable by ANDES, which parses v32/v33/v34:
      - header version set to 34 and file cut right after the induction machine block (the trailing node-breaker
        substation blocks are unknown to ANDES), terminated by 'Q';
      - generator records: drop the NREG column. ANDES reads generator columns with the v33 layout, so with NREG
        present it would take RMPCT as Pmax, PT as Pmin and the GTAP tap ratio as the in-service status;
      - generator voltage setpoints VS are replaced by the solved voltage of their bus. ANDES resets bus voltages to
        VS at start-up, and on this network (branches of ~1e-4 pu impedance) a 1e-3 pu difference (Q-limited or
        remote-regulating generators) is enough to ruin the start point. This makes the test about the passive
        network model (impedances, taps, shunts, topology) and not about generator voltage control;
      - line end shunts (GI, BI, GJ, BJ of in-service branches) are added as fixed shunts at their buses: the ANDES
        RAW reader ignores these fields (only reads the total B, which powsybl writes as 0), so all line charging
        would be lost;
      - buses of type 3 (slack) that have no generator get a zero-output generator. powsybl may pick a bus without
        generator as reference bus (as OpenLoadFlow does) but ANDES defines its slack from a generator;
      - if kept_bus_numbers is given, buses outside it and every element touching them are removed (ANDES cannot
        solve a network with islands that have no slack: the Jacobian is singular and all results are NaN).
    """
    raw_lines = raw_path.read_text().splitlines()
    header_fields = raw_lines[0].split("/")[0].split(",")
    header_fields[2] = "34"
    raw_lines[0] = ",".join(header_fields)

    end_of_standard_data_index = next(
        (line_index for line_index, line in enumerate(raw_lines) if line.startswith("0 / END OF INDUCTION MACHINE DATA")),
        len(raw_lines) - 1,
    )
    raw_lines = raw_lines[: end_of_standard_data_index + 1]

    def is_kept(*bus_numbers: str) -> bool:
        return kept_bus_numbers is None or all(int(bus_number) in kept_bus_numbers for bus_number in bus_numbers)

    base_mva = float(header_fields[1])
    line_end_shunts_by_bus_number = collect_line_end_shunts(raw_lines, is_kept)

    nreg_column_index = 8
    output_lines = raw_lines[:3]
    current_block = "SYSTEM-WIDE"
    slack_bus_numbers: dict[str, str] = {}  # bus number -> voltage setpoint, for type 3 buses
    solved_voltage_by_bus_number: dict[str, str] = {}
    buses_with_generator: set[str] = set()

    line_index = 3
    while line_index < len(raw_lines):
        line = raw_lines[line_index]
        if line.startswith("0 /"):
            if current_block == "FIXED SHUNT":
                for bus_number, (conductance_pu, susceptance_pu) in line_end_shunts_by_bus_number.items():
                    # I,ID,STATUS,GL(MW at 1 pu),BL(Mvar at 1 pu)
                    output_lines.append(
                        f"{bus_number},'LC',1,{conductance_pu * base_mva!r},{susceptance_pu * base_mva!r}"
                    )
            if current_block == "GENERATOR":
                for bus_number, voltage_setpoint_pu in slack_bus_numbers.items():
                    if bus_number not in buses_with_generator:
                        print(f"[raw] slack bus {bus_number} has no generator: adding a zero-output slack generator")
                        # I,ID,PG,QG,QT,QB,VS,IREG,MBASE,ZR,ZX,RT,XT,GTAP,STAT,RMPCT,PT,PB
                        output_lines.append(
                            f"{bus_number},'99',0.0,0.0,9999.0,-9999.0,{voltage_setpoint_pu},0,100.0,0.0,1.0,0.0,0.0,"
                            "1.0,1,100.0,9999.0,-9999.0"
                        )
            output_lines.append(line)
            next_block = re.search(r"BEGIN (.*?) DATA", line)
            current_block = next_block.group(1) if next_block else "END"
            line_index += 1
            continue

        fields = line.split(",")
        if current_block == "BUS":
            if is_kept(fields[0]):
                output_lines.append(line)
                solved_voltage_by_bus_number[fields[0].strip()] = fields[7].strip()
                if fields[3].strip() == "3":
                    slack_bus_numbers[fields[0].strip()] = fields[7].strip()
        elif current_block in ("LOAD", "FIXED SHUNT", "SWITCHED SHUNT"):
            if is_kept(fields[0]):
                output_lines.append(line)
        elif current_block == "GENERATOR":
            if is_kept(fields[0]):
                buses_with_generator.add(fields[0].strip())
                fields[6] = solved_voltage_by_bus_number[fields[0].strip()]  # VS := solved bus voltage
                del fields[nreg_column_index]
                output_lines.append(",".join(fields))
        elif current_block == "BRANCH":
            if is_kept(fields[0], fields[1]):
                output_lines.append(line)
        elif current_block == "TRANSFORMER":
            record_line_count = 4 if int(fields[2]) == 0 else 5
            terminal_bus_numbers = [bus for bus in fields[:3] if int(bus) != 0]
            if is_kept(*terminal_bus_numbers):
                output_lines.extend(raw_lines[line_index : line_index + record_line_count])
            line_index += record_line_count
            continue
        else:
            output_lines.append(line)
        line_index += 1

    converted_path = raw_path.with_name(raw_path.stem + "_andes.raw")
    converted_path.write_text("\n".join(output_lines + ["Q"]) + "\n")
    return converted_path


def run_andes_power_flow(raw_path: Path):
    """
    First pass loads the whole network to find its largest island; the file is then rewritten without the
    other islands (which have no slack) and ANDES is run on the remaining main island.
    """
    full_system = andes.load(str(rewrite_raw_for_andes(raw_path)), setup=True, no_output=True, default_config=True)
    main_island = max(full_system.Bus.island_sets, key=len)
    main_island_bus_numbers = {int(full_system.Bus.idx.v[position]) for position in main_island}
    print(f"[andes] main island: {len(main_island_bus_numbers)} buses out of {full_system.Bus.n}")

    andes_system = andes.load(
        str(rewrite_raw_for_andes(raw_path, main_island_bus_numbers)),
        setup=True, no_output=True, default_config=True,
    )
    andes_system.PFlow.run()
    print(f"[andes] power flow converged: {andes_system.PFlow.converged}")
    return andes_system


def compare_global_balance(network, andes_system, slack_mismatch_mw: float) -> None:
    """Compare totals on the main synchronous component only (ANDES is run on the main island)."""
    base_mva = andes_system.config.mva
    buses = network.get_buses()
    main_component_bus_ids = set(buses.index[buses["synchronous_component"] == 0])

    loads = network.get_loads()
    loads = loads[loads["bus_id"].isin(main_component_bus_ids)]
    generators = network.get_generators()
    generators = generators[generators["bus_id"].isin(main_component_bus_ids) & generators["connected"]]
    ps_loads_mw = loads["p"].sum()
    # The generators' p are their setpoints: the slack bus absorbs the active power mismatch on top of them.
    ps_generation_mw = -generators["p"].sum() + slack_mismatch_mw
    ps_losses_mw = ps_generation_mw - ps_loads_mw

    online_load_p0 = np.array(andes_system.PQ.p0.v) * np.array(andes_system.PQ.u.v)
    andes_loads_mw = float(online_load_p0.sum()) * base_mva
    andes_generation_mw = (
        float(np.sum(np.array(andes_system.PV.p.v) * np.array(andes_system.PV.u.v)))
        + float(np.sum(np.array(andes_system.Slack.p.v) * np.array(andes_system.Slack.u.v)))
    ) * base_mva
    andes_losses_mw = andes_generation_mw - andes_loads_mw

    summary = pd.DataFrame(
        {
            "pypowsybl": [ps_loads_mw, ps_generation_mw, ps_losses_mw],
            "andes": [andes_loads_mw, andes_generation_mw, andes_losses_mw],
        },
        index=["total load (MW)", "total generation (MW)", "losses (MW)"],
    )
    summary["difference"] = summary["andes"] - summary["pypowsybl"]
    print("\n=== Global balance (main synchronous component) ===")
    print(summary.round(2).to_string())
    print(
        f"\nElement counts  pypowsybl (all components): {len(network.get_bus_breaker_view_buses())} buses, "
        f"{len(network.get_lines())} lines, {len(network.get_2_windings_transformers())} 2wt  |  "
        f"andes (main island): {andes_system.Bus.n} buses, {andes_system.Line.n} lines/transformers"
    )


def match_andes_buses_to_pypowsybl(network, andes_system) -> pd.DataFrame:
    """Match buses on the (truncated) pypowsybl calculated bus id, which powsybl writes as the RAW bus name."""
    buses = network.get_buses()
    main_component_buses = buses[(buses["synchronous_component"] == 0) & buses["v_mag"].notna()].copy()
    main_component_buses["truncated_id"] = [bus_id[:RAW_BUS_NAME_LENGTH].strip() for bus_id in main_component_buses.index]

    andes_buses = pd.DataFrame(
        {
            "andes_bus_idx": list(andes_system.Bus.idx.v),
            "raw_bus_name": [str(name).strip() for name in andes_system.Bus.name.v],
            "v_andes_pu": andes_system.Bus.v.v,
            "angle_andes_deg": np.degrees(andes_system.Bus.a.v),
        }
    )

    matched = main_component_buses.reset_index().rename(columns={"id": "pypowsybl_bus_id"}).merge(
        andes_buses, left_on="truncated_id", right_on="raw_bus_name", how="inner"
    )
    # Truncation can create ambiguous matches: keep only unambiguous ones.
    matched = matched.drop_duplicates(subset="truncated_id", keep=False)
    print(f"\n[matching] {len(matched)} / {len(main_component_buses)} main-component buses matched to ANDES buses by name")
    return matched


def compare_bus_voltages(network, matched: pd.DataFrame) -> None:
    if matched.empty:
        print("[voltages] no bus could be matched by name; check Bus.name in the RAW file.")
        return

    voltage_levels = network.get_voltage_levels()["nominal_v"]
    matched = matched.copy()
    matched["nominal_voltage_kv"] = matched["voltage_level_id"].map(voltage_levels)
    matched["v_pypowsybl_pu"] = matched["v_mag"] / matched["nominal_voltage_kv"]

    # Angles are relative to each solver's own slack: remove the median offset between the two solutions
    # (robust to a few badly converted buses, unlike re-referencing on a single bus).
    median_angle_offset_deg = (matched["angle_andes_deg"] - matched["v_angle"]).median()
    matched["angle_pypowsybl_deg"] = matched["v_angle"] + median_angle_offset_deg

    matched["voltage_error_pu"] = (matched["v_andes_pu"] - matched["v_pypowsybl_pu"]).abs()
    matched["angle_error_deg"] = (matched["angle_andes_deg"] - matched["angle_pypowsybl_deg"]).abs()
    matched = matched.dropna(subset=["voltage_error_pu", "angle_error_deg"])

    print("\n=== Bus voltage comparison ===")
    print(f"max |dV|     = {matched['voltage_error_pu'].max():.5f} pu   (tolerance {VOLTAGE_TOLERANCE_PU})")
    print(f"mean |dV|    = {matched['voltage_error_pu'].mean():.5f} pu")
    print(f"max |dAngle| = {matched['angle_error_deg'].max():.4f} deg  (tolerance {ANGLE_TOLERANCE_DEG})")
    print(
        f"buses within tolerance: dV {(matched['voltage_error_pu'] < VOLTAGE_TOLERANCE_PU).mean():.1%}, "
        f"dAngle {(matched['angle_error_deg'] < ANGLE_TOLERANCE_DEG).mean():.1%}"
    )

    print("\nError by nominal voltage (kV):")
    print(matched.groupby("nominal_voltage_kv")[["voltage_error_pu", "angle_error_deg"]].agg(["count", "mean", "max"]).round(4).to_string())

    print("\nWorst 10 buses by voltage error:")
    worst_columns = ["pypowsybl_bus_id", "v_pypowsybl_pu", "v_andes_pu", "voltage_error_pu", "angle_error_deg"]
    print(matched.nlargest(10, "voltage_error_pu")[worst_columns].to_string(index=False))

    fraction_within_voltage_tolerance = (matched["voltage_error_pu"] < VOLTAGE_TOLERANCE_PU).mean()
    fraction_within_angle_tolerance = (matched["angle_error_deg"] < ANGLE_TOLERANCE_DEG).mean()
    conversion_ok = min(fraction_within_voltage_tolerance, fraction_within_angle_tolerance) >= MIN_FRACTION_OF_BUSES_WITHIN_TOLERANCE
    print(
        "\nVERDICT:",
        "passive network conversion looks satisfying (check the worst buses above)"
        if conversion_ok
        else "conversion NOT satisfying (see tables above)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("network_path", nargs="?", default=DEFAULT_NETWORK_PATH)
    parser.add_argument("--keep-dir", type=Path, default=None, help="Keep the exported RAW file in this directory")
    arguments = parser.parse_args()

    network, slack_mismatch_mw = run_pypowsybl_reference(arguments.network_path)

    with tempfile.TemporaryDirectory() as temporary_directory:
        output_directory = arguments.keep_dir or Path(temporary_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        raw_path = export_to_psse_raw(network, output_directory)
        andes_system = run_andes_power_flow(raw_path)
        compare_global_balance(network, andes_system, slack_mismatch_mw)
        matched = match_andes_buses_to_pypowsybl(network, andes_system)
        compare_bus_voltages(network, matched)


if __name__ == "__main__":
    main()
