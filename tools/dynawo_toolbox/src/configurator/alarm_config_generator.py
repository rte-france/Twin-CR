"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Generate the alarm configuration (alarms.json, see schemas/alarms.json) read by the Orchestrator AlarmDetector.

Alarms are generated from the outputs of the game master and of the SCADA (same ids, but the game master has more), so
that both sides have the same alarms, each side only seeing the ids it receives:
  - "breaker"/"disconnector"/"line": the state outputs (kind "state") of Dynawo, by IIDM equipment type
    (Dynawo state encoding: 1 = open, 2 = closed, 3/4 = closed on side 1/2 only);
  - "ground_disconnector": the state outputs of the asset simulator (bool, true = open);
  - "overload": the OverloadAlarm assets of the asset simulator config (bool, true = overload);
  - "current": the current outputs (kind "i") whose equipment side has IIDM current limits, one
    threshold level per limit (permanent limit first, then the temporary limits in increasing value; beyond
    MAX_CURRENT_LEVELS, the permanent limit and the highest temporary limits);
  - "voltage": the bus voltage outputs (kind "U" without side, in kV) of the busbar sections (node-breaker voltage
    levels, not the feeder nodes) or buses (bus-breaker voltage levels) of the voltage levels with IIDM voltage limits,
    a low and a high threshold level (lowVoltageLimit, highVoltageLimit), with a 0.5% hysteresis. A zero voltage
    (de-energised) does not alarm.

Each alarm names its IIDM equipment ("equipment_id"): the backends locate it in the substation of their own network.

The types are generic defaults (English labels, priorities made up). A context with its own conventions
can build its own types and reuse the entry builders.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import pypowsybl as pp

from json_io import load_json

Entry = dict[str, Any]

ALARM_CONFIG_NAME = "alarms.json"

# Maximum number of threshold levels of the "current" type
MAX_CURRENT_LEVELS = 4


def default_priorities() -> list[dict[str, Any]]:
    """Colour and sound from the priority: the rule with the highest "min" not above the priority applies."""
    return [
        {"min": 0, "color": "grey", "sound": None},
        {"min": 3, "color": "yellow", "sound": "yellow"},
        {"min": 15, "color": "red", "sound": "red"},
        {"min": 40, "color": "violet", "sound": "violet"},
    ]


def default_types() -> dict[str, Any]:
    open_state = {"label": "Open", "priority": 7, "color": "blue", "sound": "blue"}
    closed_state = {"label": "Closed", "priority": 6, "color": "grey", "sound": "grey"}
    return {
        "breaker": {
            "mode": "momentary", "retain": False,
            "states": {"1": open_state, "2": closed_state},
        },
        "ground_disconnector": {
            "mode": "momentary", "retain": False,
            "states": {"1": {"label": "Open", "priority": 5}, "0": {"label": "Closed", "priority": 5}},
        },
        "disconnector": {
            "mode": "momentary", "retain": False,
            "states": {"1": {"label": "Open", "priority": 5}, "2": {"label": "Closed", "priority": 5}},
        },
        "line": {
            "mode": "momentary", "retain": False,
            "states": {
                "1": open_state,
                "2": closed_state,
                "3": {"label": "Closed on side 1 only", "priority": 7},
                "4": {"label": "Closed on side 2 only", "priority": 7},
            },
        },
        "overload": {  # Also in the OverloadMonitor while on
            "mode": "persistent", "retain": True, "normal": 0, "monitor": True,
            "states": {"1": {"label": "Start", "priority": 19}, "0": {"label": "End", "priority": 4}},
        },
        "current": {
            "mode": "momentary", "retain": False,
            "normal_state": {"label": "Overload end", "priority": 0},
            "levels": [
                {"name": f"LIMIT{i}", "label": f"Limit {i} overload", "priority": 10 + 5 * (i - 1)}
                for i in range(1, MAX_CURRENT_LEVELS + 1)
            ],
        },
        "voltage": {
            "mode": "momentary", "retain": False, "hysteresis": 0.005,
            "normal_state": {"label": "Voltage normal", "priority": 0},
            "levels": [
                {"name": "LOW", "direction": "low", "label": "Low voltage", "priority": 10},
                {"name": "HIGH", "direction": "high", "label": "High voltage", "priority": 10},
            ],
        },
    }


def default_commands() -> dict[str, Any]:
    return {"enabled": True, "label": "Command", "priority": 2}


class NetworkIndex:
    """Equipment type of the IIDM equipments, and busbars."""

    def __init__(self, network: pp.network.Network) -> None:
        self.switch_kind = network.get_switches()["kind"].to_dict()  # BREAKER, DISCONNECTOR, LOAD_BREAK_SWITCH
        self.lines = set(network.get_lines().index)
        self.busbar_sections = set(network.get_busbar_sections().index)
        self.bus_breaker_voltage_levels = set(
            network.get_voltage_levels(attributes=["topology_kind"]).query("topology_kind == 'BUS_BREAKER'").index)

    def is_busbar(self, output: Entry) -> bool:
        """Voltage output of a busbar: a busbar section, or a bus of a bus-breaker voltage level."""
        return (output.get("equipmentId") in self.busbar_sections
                or output.get("voltage_level") in self.bus_breaker_voltage_levels)


def current_limits(network: pp.network.Network) -> dict[tuple[str, str], list[float]]:
    """(element id, side) -> current limit values in increasing order (permanent limit first)."""
    df = network.get_operational_limits().reset_index()
    df = df[(df["type"] == "CURRENT") & df["value"].between(0, 1e9, inclusive="neither")]
    limits = {}
    for (element_id, side), group in df.groupby(["element_id", "side"]):
        if not (group["acceptable_duration"] == -1).any():
            continue  # Temporary limits alone are not limits on their own
        limits[(element_id, side)] = sorted(set(float(v) for v in group["value"]))
    return limits


def voltage_limits(network: pp.network.Network) -> dict[str, dict[str, float]]:
    """Voltage level id -> voltage limits (kV) by level name of the "voltage" type (LOW, HIGH), when set."""
    df = network.get_voltage_levels(attributes=["low_voltage_limit", "high_voltage_limit"])
    limits = {}
    for vl_id, row in df.iterrows():
        vl_limits = {name: float(value) for name, value in (("LOW", row["low_voltage_limit"]),
                                                            ("HIGH", row["high_voltage_limit"]))
                     if 0 < value < 1e9}  # NaN when not set
        if vl_limits:
            limits[vl_id] = vl_limits
    return limits


def state_entries(outputs: list[Entry], index: NetworkIndex) -> list[Entry]:
    """Breakers, disconnectors and lines from the state outputs."""
    entries = []
    for output in outputs:
        if output.get("kind") != "state" or "equipmentId" not in output:
            continue
        equipment_id = output["equipmentId"]
        switch_kind = index.switch_kind.get(equipment_id)
        if output.get("simulator") == "asset_simulator":
            alarm_type = "ground_disconnector"
        elif switch_kind == "BREAKER":
            alarm_type = "breaker"
        elif switch_kind is not None:
            alarm_type = "disconnector"
        elif equipment_id in index.lines:
            alarm_type = "line"
        else:
            continue
        entry = {"id": output["id"], "type": alarm_type, "label": equipment_id, "equipment_id": equipment_id}
        if alarm_type == "ground_disconnector" and output.get("topic"):
            # The backends add the ground disconnectors to their network, but may skip some: their substation (the
            # topic of the asset simulator outputs) is the fallback of Locate
            entry["substation_id"] = output["topic"]
        entries.append(entry)
    return entries


def overload_entries(asset_simulator_config: list[Entry], outputs: list[Entry]) -> list[Entry]:
    """OverloadAlarm assets, keyed by the id they publish, on the equipment of the current they monitor."""
    outputs_by_id = {o["id"]: o for o in outputs if o.get("equipmentId")}
    entries = []
    for asset in asset_simulator_config:
        if asset.get("type") != "OverloadAlarm":
            continue
        entry = {"id": asset["alarm_key"], "type": "overload", "label": asset["alarm_key"]}
        current = outputs_by_id.get(asset.get("current_key"))
        if current is not None:
            entry["equipment_id"] = current["equipmentId"]
            if current.get("side"):
                entry["side"] = current["side"]
        entries.append(entry)
    return entries


def current_entries(outputs: list[Entry],
                    limits: dict[tuple[str, str], list[float]]) -> list[Entry]:
    """Current outputs with limits, one threshold level per limit."""
    level_names = [level["name"] for level in default_types()["current"]["levels"]]
    entries = []
    for output in outputs:
        if output.get("kind") != "i" or "equipmentId" not in output:
            continue
        equipment_id, side = output["equipmentId"], output.get("side")
        if side is None:
            continue
        values = limits.get((equipment_id, side))
        if not values:
            continue
        if len(values) > len(level_names):
            # Keep the permanent limit and the most severe temporary limits
            values = values[:1] + values[len(values) - len(level_names) + 1:]
        side_label = {"ONE": " side 1", "TWO": " side 2"}.get(side or "", "")
        entries.append({
            "id": output["id"],
            "type": "current",
            "label": f"{equipment_id} I{side_label}",
            "equipment_id": equipment_id,
            "side": side,
            "thresholds": dict(zip(level_names, values)),
        })
    return entries


def voltage_entries(outputs: list[Entry], limits: dict[str, dict[str, float]], index: NetworkIndex) -> list[Entry]:
    """Busbar voltage outputs of the voltage levels with voltage limits, located by their voltage level."""
    entries = []
    for output in outputs:
        if output.get("kind") != "U" or not output.get("equipmentId") or output.get("side"):
            continue  # Not a bus voltage (the branch end voltages have a side)
        if not index.is_busbar(output):
            continue  # Feeder node of a node-breaker voltage level
        thresholds = limits.get(output.get("voltage_level"))
        if not thresholds:
            continue
        entries.append({
            "id": output["id"],
            "type": "voltage",
            "label": f"{output['equipmentId']} U",
            "equipment_id": output["voltage_level"],
            "thresholds": thresholds,
        })
    return entries


def merge_outputs(*output_lists: list[Entry]) -> list[Entry]:
    """Outputs of several files, once per id (first one kept)."""
    merged: dict[str, Entry] = {}
    for outputs in output_lists:
        for output in outputs:
            merged.setdefault(output["id"], output)
    return list(merged.values())


def generate(iidm_path: str | Path, scada_outputs_path: str | Path, output_path: str | Path,
             asset_simulator_config_path: str | Path | None = None,
             game_master_outputs_path: str | Path | None = None) -> Path:
    network = pp.network.load(str(iidm_path))
    index = NetworkIndex(network)
    outputs = merge_outputs(
        load_json(game_master_outputs_path) if game_master_outputs_path is not None else [],
        load_json(scada_outputs_path),
    )

    alarms = state_entries(outputs, index)
    if asset_simulator_config_path is not None and Path(asset_simulator_config_path).exists():
        alarms += overload_entries(load_json(asset_simulator_config_path), outputs)
    alarms += current_entries(outputs, current_limits(network))
    alarms += voltage_entries(outputs, voltage_limits(network), index)

    config = {
        "priorities": default_priorities(),
        "types": default_types(),
        "commands": default_commands(),
        "alarms": alarms,
    }
    output_path = Path(output_path)
    with open(output_path, "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"Alarm config: {len(alarms)} alarms written to {output_path}")
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate the alarm configuration of the AlarmDetector")
    parser.add_argument("--iidm", required=True, help="IIDM file (equipment types, current and voltage limits)")
    parser.add_argument("--scada_outputs", required=True, help="scada_outputs json file")
    parser.add_argument("--game_master_outputs", help="game_master_outputs json file")
    parser.add_argument("--asset_simulator_config", help="Asset simulator config (OverloadAlarm assets)")
    parser.add_argument("--output", default=ALARM_CONFIG_NAME, help="Output file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate(args.iidm, args.scada_outputs, args.output, args.asset_simulator_config, args.game_master_outputs)
