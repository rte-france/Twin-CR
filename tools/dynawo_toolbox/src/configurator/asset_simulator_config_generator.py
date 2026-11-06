"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Build asset_simulator_config.json and expand scada_inputs.json from an IIDM
network, a dynawo_gamem_aster_outputs.json, and a list of TI's (telemetry/
telecommand points).

For every TI with type in {TS, TM, OM} and bayt == "ProtectionEquipment" or "GroundDisconnector":
  - default entry: type "ValueHolder"
  - if TI["typ"] is one of AL.SUR.1 / AL.SUR.5 / AL.SUR10 / AL.SUR20:
    entry: type "OverloadAlarm", with max_current read from the operational
    limits of the line/transformer associated with TI["iidm"] (a switch id).

For every TS/TM TI that got an asset entry, if a TC (for TS) or TVC (for TM)
TI shares the same "dv", a scada_input entry is generated for it.

The ground disconnectors also get an entry in game_master_inputs.json and in both output
files, and name the switch they command in scada_inputs.json, with "asset_simulator" as their simulator.
"""

import argparse
import json

from typing import Any

import pandas as pd
import pypowsybl as pp

ASSET_SIMULATOR = "asset_simulator"
SIMULATED_TYPES = ("TS", "OM")

from json_io import load_json
from handlers.iidm_handler import IIDMHandler

OVERLOAD_TYPE_DURATION_SECONDS = {
    "AL.SUR.1": 60 * 1,
    "AL.SUR.5": 60 * 5,
    "AL.SUR10": 60 * 10,
    "AL.SUR20": 60 * 20,
}

TI = dict[str, Any]


def save_json(path: str, data: Any) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


def side_to_str(side: int | str) -> str:
    if isinstance(side, str):
        return side
    if side == 1:
        return "ONE"
    if side == 2:
        return "TWO"
    if side == 3:
        return "THREE"
    raise ValueError("Invalid side:", side)


class SubstationResolver:
    """
    Resolves TI["bayiidm"] to a substation id, whether it's already a substation id or a voltage level id.
    """
    def __init__(self, n: pp.network.Network) -> None:
        self.substation_ids = set(n.get_substations().index)
        self.voltage_levels = n.get_voltage_levels()

    def resolve(self, bayiidm: str) -> str | None:
        if bayiidm in self.substation_ids:
            return bayiidm
        if bayiidm in self.voltage_levels.index:
            return self.voltage_levels.loc[bayiidm, "substation_id"]
        return None



def build_asset_simulator_config_entry(
    ti: TI,
    know_rtus: set[str],
    substation_resolver: SubstationResolver,
    limits_map: dict[tuple[str, str], dict[int, float]],
    dynawo_index: dict[tuple[str, str], str],
) -> dict[str, Any] | None:

    location = ti.get("ru") or "SCADA"  # TI's without a RTU (e.g. manual commands OM's) are put directly in the SCADA
    if location not in know_rtus:
        return None
    topic = substation_resolver.resolve(ti["bayiidm"])
    if topic is None:
        return None

    entry = {
        "location": location,
        "topic": topic,
        "destination": "SCADA",
        "key": ti["libelle"],
    }
    if ti.get("bayt") == "GroundDisconnector":
        # Ground disconnectors are open at startup
        entry["value"] = True

    if ti.get("tase2"):
        entry["tase2"] = {"signalisation_type": ti["type"], "tase2_id": ti["tase2"]}

    if ti.get("typ") in OVERLOAD_TYPE_DURATION_SECONDS:
        # TI typ matches an OverloadAlarm
        entry["type"] = "OverloadAlarm"
        duration_seconds = OVERLOAD_TYPE_DURATION_SECONDS.get(ti["typ"])

        equipment_id = ti["iidm"]
        side = ti.get("side")
        if side is None:
            sides_priority = ["ONE", "TWO", "THREE"]
        else:
            side = side_to_str(ti["side"])
            sides_priority = [side] + [s for s in ["ONE", "TWO", "THREE"] if s != side]  # Search first the actual side, fallback to other sides if exist

        max_current = None
        for s in sides_priority:
            max_current = limits_map.get((equipment_id, s), {}).get(duration_seconds)
            if max_current is not None:
                side = s
                break

        if max_current is None:
            print(f"WARNING: no operational limit for {equipment_id} at duration {duration_seconds}s (TI {ti['libelle']!r}), skipping")
            return None

        current_key = dynawo_index.get((equipment_id, side))
        if current_key is None:
            print(f"WARNING: no dynawo_output found for {(equipment_id, side)} (TI {ti['libelle']!r}), skipping")
            return None
        entry |= {
            "current_key": current_key,
            "alarm_key": ti["libelle"],
            "max_current": max_current,
        }

    else:
        # Default model for most TI's
        entry["type"] = "ValueHolder"
        entry["key"] =  ti["libelle"]

    return entry


def build_scada_input_entries(ti_list: list[TI], know_rtus: set[str], added_ts_tm_libelle: dict[tuple[str, str], str],
                              switch_id_by_libelle: dict[str, str]) -> list[dict[str, Any]]:
    """
    Build the scada_input entries for TC/TVC counterparts of added TS/TM by matching ti["dv"].
    "id" is the libelle of the original TS/TM, not the TC/TVC's own libelle.
    A ground disconnector also names the switch it commands, which is what the SCADA backend draws.
    """
    counterpart_to_ts_tm = {"TC": "TS", "TVC": "TM"}
    new_entries = []
    for ti in ti_list:
        ts_tm_type = counterpart_to_ts_tm.get(ti["type"])
        if ts_tm_type is None:
            continue
        if not ti.get("dv"):  # TODO: no "dv" in TVC's, so need to match in another way
            continue
        ts_tm_libelle = added_ts_tm_libelle.get((ti["dv"], ts_tm_type))
        if ts_tm_libelle is None:
            continue
        if ti["ru"] not in know_rtus:
            print("Warning:", ti["ru"], "not in know RTUs")
            continue
        entry = {
            "id": ts_tm_libelle,
            "destination": ti["ru"],
            "tase2": ti["tase2"],
            "simulator": ASSET_SIMULATOR,
        }
        switch_id = switch_id_by_libelle.get(ts_tm_libelle)
        if switch_id is not None:
            entry["equipmentId"] = switch_id
            entry["kind"] = "state"
        new_entries.append(entry)
    return new_entries


def add_entries(path: str, entries: list[dict[str, Any]]) -> None:
    """
    Add the asset simulator entries to a file the configurator wrote, replacing the ones already there.

    The configurator rewrites those files on every run, but the generator can also be run on its own,
    and then the entries of the previous run are the ones to drop.
    """
    if not entries:
        return
    kept = [e for e in load_json(path) if e.get("simulator") != ASSET_SIMULATOR]
    save_json(path, kept + entries)


def build_output_entries(ti_list: list[TI], switch_id_by_libelle: dict[str, str],
                         substation_resolver: "SubstationResolver",
                         know_rtus: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Build the game master and the SCADA output entries of the ground disconnectors the asset
    simulator holds, in that order.

    The backends read them the way they read a Dynawo output, which is what puts the state the asset
    simulator publishes on the right switch. They name "asset_simulator" as their simulator, so the
    orchestrator leaves them alone. Only the TI's the asset simulator actually holds get an entry, so
    the same RTU condition as the asset configuration applies.
    """
    game_master_entries = []
    scada_entries = []
    seen = set()
    for ti in ti_list:
        switch_id = switch_id_by_libelle.get(ti["libelle"]) if ti["type"] in SIMULATED_TYPES else None
        if switch_id is None or ti["bayt"] != "GroundDisconnector" or switch_id in seen:
            continue
        location = ti.get("ru") or "SCADA"
        if location not in know_rtus:
            continue
        topic = substation_resolver.resolve(ti["bayiidm"])
        if topic is None:
            continue
        seen.add(switch_id)
        entry = {
            "id": ti["libelle"],
            "equipmentId": switch_id,
            "kind": "state",
            "topic": topic,
            "simulator": ASSET_SIMULATOR,
        }
        game_master_entries.append({**entry, "voltage_level": ti["bayiidm"]})
        scada_entries.append({**entry, "source": location, "destination": "SCADA"})
    return game_master_entries, scada_entries


def build_ground_disconnector_switch_ids(ti_list: list[TI], network: pp.network.Network) -> dict[str, str]:
    """
    Map the libelle of every simulated ground disconnector to the switch that stands for it.
    """
    switch_ids = set(network.get_switches().index)
    voltage_level_ids = set(network.get_voltage_levels().index)
    switch_id_by_libelle = {}
    for ti in ti_list:
        if ti["type"] not in SIMULATED_TYPES or ti["bayt"] != "GroundDisconnector" or not ti.get("libelle"):
            continue
        voltage_level_id = ti.get("bayiidm")
        if voltage_level_id not in voltage_level_ids:
            continue
        switch_id = f"{voltage_level_id}_{ti['libelle']}"
        if switch_id in switch_ids:
            continue
        switch_id_by_libelle[ti["libelle"]] = switch_id
    return switch_id_by_libelle


def generate(
    iidm_path: str,
    dynawo_outputs_path: str,
    communication_file: str,
    timapped_path: str,
    scada_inputs_path: str,
    asset_simulator_config_output_path: str,
    game_master_inputs_path: str,
    game_master_outputs_path: str,
    scada_outputs_path: str,
) -> None:
    n = pp.network.load(iidm_path)
    ti_list: list[TI] = load_json(timapped_path)
    dynawo_outputs: list[dict[str, Any]] = load_json(dynawo_outputs_path)

    iidm_handler = IIDMHandler(iidm_path)
    limits_map = iidm_handler.build_current_limits_map()
    substation_resolver = SubstationResolver(n)
    dynawo_index = {(o["equipmentId"], o["side"]): o["id"] for o in dynawo_outputs if "equipmentId" in o and "side" in o}

    rtus = set()
    communications = json.load(open(communication_file))
    links = communications["links"]
    for link in links:
        from_ = link["from"]
        to = link["to"]
        rtus.add(from_)
        rtus.add(to)

    asset_config = []
    added_ts_tm_libelle: dict[tuple[str, str], str] = {}

    for ti in ti_list:
        ti_type = ti["type"]
        if ti_type is None:
            continue
        if ti_type not in ("TS", "TM", "OM") or ti["bayt"] not in  ["ProtectionEquipment", "GroundDisconnector"]:
            continue
        entry = build_asset_simulator_config_entry(ti, rtus, substation_resolver, limits_map, dynawo_index)
        if entry is None:
            continue
        asset_config.append(entry)
        if ti_type in ("TS", "TM") and ti.get("dv"):
            added_ts_tm_libelle[(ti["dv"], ti_type)] = ti["libelle"]

    save_json(asset_simulator_config_output_path, asset_config)

    switch_id_by_libelle = build_ground_disconnector_switch_ids(ti_list, n)

    new_scada_entries = build_scada_input_entries(ti_list, rtus, added_ts_tm_libelle, switch_id_by_libelle)
    add_entries(scada_inputs_path, new_scada_entries)

    new_game_master_entries = [
        {"equipmentId": switch_id, "kind": "state", "id": libelle, "simulator": ASSET_SIMULATOR}
        for libelle, switch_id in switch_id_by_libelle.items()
    ]
    add_entries(game_master_inputs_path, new_game_master_entries)

    new_game_master_outputs, new_scada_outputs = build_output_entries(
        ti_list, switch_id_by_libelle, substation_resolver, rtus)
    add_entries(game_master_outputs_path, new_game_master_outputs)
    add_entries(scada_outputs_path, new_scada_outputs)

    print(f"asset_simulator_config: {len(asset_config)} entries -> {asset_simulator_config_output_path}")
    print(f"scada_inputs: {len(new_scada_entries)} new entries added -> {scada_inputs_path}")
    print(f"game_master_inputs: {len(new_game_master_entries)} new entries added -> {game_master_inputs_path}")
    print(f"outputs: {len(new_game_master_outputs)} new entries added -> {game_master_outputs_path}"
          f" and {len(new_scada_outputs)} -> {scada_outputs_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iidm_path")
    parser.add_argument("dynawo_outputs_path")
    parser.add_argument("communication_file")
    parser.add_argument("timapped_path")
    parser.add_argument("scada_inputs_path", help="existing scada_inputs.json, expanded in place")
    parser.add_argument("asset_simulator_config_output_path")
    parser.add_argument("game_master_inputs_path", help="existing game_master_inputs.json, expanded in place")
    parser.add_argument("game_master_outputs_path", help="existing game_master_outputs.json, expanded in place")
    parser.add_argument("scada_outputs_path", help="existing scada_outputs.json, expanded in place")
    args = parser.parse_args()

    generate(
        args.iidm_path,
        args.dynawo_outputs_path,
        args.communication_file,
        args.timapped_path,
        args.scada_inputs_path,
        args.asset_simulator_config_output_path,
        args.game_master_inputs_path,
        args.game_master_outputs_path,
        args.scada_outputs_path,
    )
