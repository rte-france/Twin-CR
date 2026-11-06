"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import logging
from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
from io import StringIO, BytesIO
from pathlib import Path
from typing import Union, DefaultDict, Literal

from lxml import etree

from dynawopy.base import TestcaseUpdater_Base, bfs_nearest

logger = logging.getLogger(__name__)

from dataclasses import dataclass


@dataclass(frozen=True)
class _LovrTopology:
    busbar_section_id: str
    equipment_id: str
    line_side: int
    switch_id: str
    voltage_level_id: str

class TestcaseUpdater(TestcaseUpdater_Base):

    __test__ = False

    def __init__(self, *args, existing_lovr_lib: DefaultDict[str, set[str]] | None | Literal[True] = None, **kwargs):
        super().__init__(*args, **kwargs)

        self._iidm_index = None
        self._vl_graph_cache = {}

        assert isinstance(existing_lovr_lib, dict) or existing_lovr_lib == True or existing_lovr_lib == None, "Please either give a dictionary or specify True or None for the existing_lovr_lib argument"

        self.existing_lovr_lib = (
            defaultdict(set) if existing_lovr_lib is True else existing_lovr_lib
        )
        if self.existing_lovr_lib is not None:
            self._init_existing_lovr_lib()

    def _init_existing_lovr_lib(self):
        lovr_models = self.xp_dyd("//dyn:blackBoxModel[@lib='LackOfVoltageRelay']")
        lovr_ids = {el.get("id") for el in lovr_models}

        # Map LOVR id -> connected var name on the other side
        lovr_to_busbarSection_var = {}

        connects_1 = self.xp_dyd("//dyn:connect")
        for conn in connects_1:
            id1 = conn.get("id1")
            id2 = conn.get("id2")
            var1 = conn.get("var1")
            var2 = conn.get("var2")

            if id1 in lovr_ids and var1 == "lackOfVoltageRelay_UMonitoredBusPu":
                lovr_to_busbarSection_var[id1] = var2
            elif id2 in lovr_ids and var2 == "lackOfVoltageRelay_UMonitoredBusPu":
                lovr_to_busbarSection_var[id2] = var1

        # Map busbarSection id -> substation id
        self._ensure_iidm_index()
        vl_by_bb = self._iidm_index["voltage_level_by_busbar_section"]
        sub_by_vl = self._iidm_index["substation_by_voltage_level"]

        for lovr_id, busbarSection_var in lovr_to_busbarSection_var.items():
            busbarSection_id = busbarSection_var.replace("_Upu_value", "")
            vl_id = vl_by_bb.get(busbarSection_id)
            if vl_id is None:
                continue
            substation_id = sub_by_vl.get(vl_id)
            if substation_id is not None:
                self.existing_lovr_lib.setdefault(substation_id, set()).add(lovr_id)


    def add_lovrs_to_substation(self, substation_id: str | Iterable, parId=None, add_retained=False):
        """substation_id can either be a str, in this case all voltage levels are considered, or an iterable where the first ID is the substation and the next IDs voltagelevels to add LOVRs to

        """
        voltagelevel_ids = None
        if not isinstance(substation_id, str):
            voltagelevel_ids = substation_id[1:]
            substation_id = substation_id[0]

        lines = self._get_lines_connected_to_substation(substation_id)

        voltage_level_contexts = {}

        # Only build topology graphs for voltage levels that actually have a line.
        for voltagelevel_id in {line_vl for _, _, _, line_vl in lines}:
            if voltagelevel_ids and not line_vl in voltagelevel_ids:
                continue

            graph, busbar_map, _, breaker_edges = self._build_vl_graph(
                voltagelevel_id
            )

            breakers_by_node = defaultdict(list)
            for (node1, node2), breaker in breaker_edges.items():
                breakers_by_node[node1].append((node2, breaker))
                breakers_by_node[node2].append((node1, breaker))

            voltage_level_contexts[voltagelevel_id] = (
                graph,
                busbar_map,
                breakers_by_node,
            )

        for line_id, line_side, line_node_no, line_vl in lines:
            if voltagelevel_ids and not line_vl in voltagelevel_ids:
                continue

            graph, busbar_map, breakers_by_node = voltage_level_contexts[
                line_vl
            ]

            matches = breakers_by_node.get(line_node_no, ())
            if len(matches) != 1:
                logger.warning(
                    f"Expected exactly one breaker adjacent to line '{line_id}' "
                    f"at node '{line_node_no}', found {len(matches)}."
                )
                continue

            breaker_other_node, breaker = matches[0]

            busbar_section = bfs_nearest(
                start_node=breaker_other_node,
                graph=graph,
                blocked_node=line_node_no,
                target_node_map=busbar_map,
            )

            if busbar_section is None:
                raise ValueError(
                    f"No busbar section found for line '{line_id}' "
                    f"in voltage level '{line_vl}'."
                )

            breaker_label = breaker.get("name") or breaker.get("id")
            if not breaker_label:
                raise ValueError(f"Breaker for line '{line_id}' has no id or name.")

            lovr_id = f"{breaker_label.replace(' DJ_OC', '')} DT.AMU"

            if add_retained and breaker.get("retained") == "false":
                breaker.set("retained", "true")

            self.add_lovr(
                lovr_id,
                busbarSection_id=busbar_section.get("id"),
                equipment_id=line_id,
                line_side=line_side,
                switch_id=breaker.get("id"),
                voltagelevel=line_vl,
                substation_id=substation_id,
                parId=parId,
            )

    def add_lovr(
        self,
        lovr_id,
        busbarSection_id=None,
        equipment_id=None,
        line_side=None,
        switch_id=None,
        voltagelevel=None,
        substation_id=None,
        parId=None,
        lovr_lib_name="LackOfVoltageRelay",
    ):
        has_busbar_equipment = (
            busbarSection_id is not None
            and equipment_id is not None
        )
        has_switch = switch_id is not None

        if not (has_busbar_equipment or has_switch):
            raise ValueError(
                "Specify either busbarSection_id + equipment_id, "
                "switch_id, or both."
            )

        topology = self._resolve_lovr_topology(
            busbarSection_id=busbarSection_id,
            equipment_id=equipment_id,
            line_side=line_side,
            switch_id=switch_id,
            voltagelevel=voltagelevel,
        )

        if substation_id is None:
            self._ensure_iidm_index()

            substation_id = self._iidm_index[
                "substation_by_voltage_level"
            ].get(topology.voltage_level_id)

        if substation_id is None:
            raise ValueError(
                f"Could not determine the substation for voltage level "
                f"'{topology.voltage_level_id}'."
            )

        existing_lovr_ids = self._get_existing_lovr_ids(
            substation_id,
            lovr_lib_name,
        )

        self._insert_blackboxmodel(
            lovr_id,
            lovr_lib_name,
            parId=parId,
            parFile=self.testcase.par_fpath.name,
        )

        self._add_lovr_connections(
            lovr_id=lovr_id,
            topology=topology,
            existing_lovr_ids=existing_lovr_ids,
        )

        self._remember_lovr(substation_id, lovr_id)

    def _load_lovr_configs(
        self,
        lovr_configs: list[dict] | Path | str,
    ) -> list[dict]:
        """Accept a Python list, a JSON array/object file, or a JSONL file."""
        if isinstance(lovr_configs, list):
            configs = lovr_configs

        elif isinstance(lovr_configs, (str, Path)):
            config_path = Path(lovr_configs)
            raw_content = config_path.read_text(encoding="utf-8").strip()

            if not raw_content:
                return []

            try:
                parsed = json.loads(raw_content)
            except json.JSONDecodeError:
                # Fall back to JSON Lines format.
                configs = []

                for line_number, raw_line in enumerate(
                    raw_content.splitlines(),
                    start=1,
                ):
                    raw_line = raw_line.strip()

                    if not raw_line:
                        continue

                    try:
                        configs.append(json.loads(raw_line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Invalid JSON in '{config_path}' "
                            f"at line {line_number}."
                        ) from exc
            else:
                configs = parsed if isinstance(parsed, list) else [parsed]

        else:
            raise TypeError(
                "lovr_configs must be a list of dictionaries or a file path."
            )

        for config_number, config in enumerate(configs, start=1):
            if not isinstance(config, dict):
                raise TypeError(
                    f"LOVR config #{config_number} must be a dictionary."
                )

        return configs

    def add_lovr_from_list(
        self,
        lovr_configs: list[dict] | Path | str,
        *,
        parId=None,
        lovr_lib_name="LackOfVoltageRelay",
    ) -> list[str]:
        """
        Add LOVRs from configuration records.

        Required fields:
        - libelle: LOVR model id
        - bay: base breaker name

        The IIDM breaker is looked up by:
        switch/@name == "<bay> DJ_OC"
        """
        added_lovr_ids = []

        for config_number, lovr_config in enumerate(
            self._load_lovr_configs(lovr_configs),
            start=1,
        ):
            lovr_id = (
                lovr_config.get("libelle")
                or lovr_config.get("dname")
            )
            bay = lovr_config.get("bay")

            if not isinstance(lovr_id, str) or not lovr_id.strip():
                raise ValueError(
                    f"LOVR config #{config_number} has no valid "
                    "'libelle' or 'dname' value."
                )

            if not isinstance(bay, str) or not bay.strip():
                raise ValueError(
                    f"LOVR config #{config_number} has no valid 'bay' value."
                )

            lovr_id = lovr_id.strip()
            bay = bay.strip()

            switch_name = (
                bay
                if bay.endswith(" DJ_OC")
                else f"{bay} DJ_OC"
            )

            # Lookup is explicitly performed by IIDM switch @name.
            breaker = self._get_cached_breaker_by_name(switch_name)

            # Use the resolved ID internally to avoid a second name ambiguity.
            breaker_id = breaker.get("id")
            if not breaker_id:
                raise ValueError(
                    f"Breaker '{switch_name}' has no IIDM id."
                )

            self.add_lovr(
                lovr_id=lovr_id,
                switch_id=breaker_id,
                parId=parId,
                lovr_lib_name=lovr_lib_name,
            )

            added_lovr_ids.append(lovr_id)

        return added_lovr_ids


    def _resolve_lovr_from_busbar_and_equipment(
        self,
        busbarSection_id,
        equipment_id,
        line_side,
        switch_id,
        voltagelevel,
    ):
        busbar_section = self._get_cached_busbar_section(busbarSection_id)
        line = self._get_cached_line(equipment_id)

        self._ensure_iidm_index()

        busbar_voltage_level_id = self._iidm_index[
            "voltage_level_by_busbar_section"
        ][busbarSection_id]

        requested_voltage_level_id = self._resolve_voltagelevel_id(
            voltagelevel
        )

        if (
            requested_voltage_level_id is not None
            and requested_voltage_level_id != busbar_voltage_level_id
        ):
            raise ValueError(
                f"Busbar section '{busbarSection_id}' belongs to voltage "
                f"level '{busbar_voltage_level_id}', not "
                f"'{requested_voltage_level_id}'."
            )

        voltage_level_id = (
            requested_voltage_level_id or busbar_voltage_level_id
        )

        if line_side is None:
            resolved_line_side = self._line_side_for_voltage_level(
                line,
                voltage_level_id,
            )
        else:
            resolved_line_side = self._normalize_line_side(line_side)

        if (
            line.get(f"voltageLevelId{resolved_line_side}")
            != voltage_level_id
        ):
            raise ValueError(
                f"Line '{equipment_id}' side {resolved_line_side} is not "
                f"connected to voltage level '{voltage_level_id}'."
            )

        if switch_id is None:
            switch = self._get_direct_breaker_for_line_side(
                line,
                resolved_line_side,
                voltage_level_id,
            )
        else:
            switch = self._get_cached_switch(switch_id)

            if (
                self._get_voltage_level_id_for_switch(switch)
                != voltage_level_id
            ):
                raise ValueError(
                    f"Switch '{switch_id}' is not in voltage level "
                    f"'{voltage_level_id}'."
                )

        resolved_busbar_section_id = busbar_section.get("id")
        resolved_equipment_id = line.get("id")
        resolved_switch_id = switch.get("id")

        if (
            resolved_busbar_section_id is None
            or resolved_equipment_id is None
            or resolved_switch_id is None
        ):
            raise ValueError("Resolved LOVR topology contains an element without an id.")

        return _LovrTopology(
            busbar_section_id=resolved_busbar_section_id,
            equipment_id=resolved_equipment_id,
            line_side=resolved_line_side,
            switch_id=resolved_switch_id,
            voltage_level_id=voltage_level_id,
        )


    def _resolve_lovr_from_switch(self, switch_id):
        switch = self._get_cached_switch(switch_id)
        voltage_level_id = self._get_voltage_level_id_for_switch(switch)

        line, busbar_section = self._find_bus_and_equipment_from_switch(
            switch,
            vl_graph=self._build_vl_graph(voltage_level_id),
        )

        resolved_line_side = self._line_side_for_voltage_level(
            line,
            voltage_level_id,
        )

        resolved_busbar_section_id = busbar_section.get("id")
        resolved_equipment_id = line.get("id")
        resolved_switch_id = switch.get("id")

        if (
            resolved_busbar_section_id is None
            or resolved_equipment_id is None
            or resolved_switch_id is None
        ):
            raise ValueError("Resolved LOVR topology contains an element without an id.")

        return _LovrTopology(
            busbar_section_id=resolved_busbar_section_id,
            equipment_id=resolved_equipment_id,
            line_side=resolved_line_side,
            switch_id=resolved_switch_id,
            voltage_level_id=voltage_level_id,
        )


    def _resolve_lovr_topology(
        self,
        busbarSection_id,
        equipment_id,
        line_side,
        switch_id,
        voltagelevel,
    ):
        has_busbar_equipment = (
            busbarSection_id is not None
            and equipment_id is not None
        )

        if has_busbar_equipment:
            return self._resolve_lovr_from_busbar_and_equipment(
                busbarSection_id=busbarSection_id,
                equipment_id=equipment_id,
                line_side=line_side,
                switch_id=switch_id,
                voltagelevel=voltagelevel,
            )

        if switch_id is None:
            raise ValueError(
                "Specify either busbarSection_id + equipment_id or switch_id."
            )

        return self._resolve_lovr_from_switch(switch_id)


    def _get_existing_lovr_ids(self, substation_id, lovr_lib_name):
        if self.existing_lovr_lib is not None:
            return tuple(
                self.existing_lovr_lib.get(substation_id, ())
            )

        self._ensure_iidm_index()

        busbar_ids = self._iidm_index[
            "busbar_sections_by_substation"
        ].get(substation_id, ())

        if not busbar_ids:
            return ()

        candidate_ids = set()

        for connect in self.xp_dyd("//dyn:connect"):
            var1 = connect.get("var1", "")
            var2 = connect.get("var2", "")

            if (
                connect.get("id1")
                and any(busbar_id in var2 for busbar_id in busbar_ids)
            ):
                candidate_ids.add(connect.get("id1"))

            if (
                connect.get("id2")
                and any(busbar_id in var1 for busbar_id in busbar_ids)
            ):
                candidate_ids.add(connect.get("id2"))

        return tuple(
            black_box_model.get("id")
            for black_box_model in self.xp_dyd("//dyn:blackBoxModel")
            if (
                black_box_model.get("lib") == lovr_lib_name
                and black_box_model.get("id") in candidate_ids
            )
        )


    def _remember_lovr(self, substation_id, lovr_id):
        if self.existing_lovr_lib is not None:
            self.existing_lovr_lib.setdefault(substation_id, set()).add(
                lovr_id
            )


    def _add_lovr_connections(
        self,
        lovr_id,
        topology,
        existing_lovr_ids,
    ):
        network_id = "NETWORK"

        monitor_connections = (
            (
                "lackOfVoltageRelay_UMonitoredBusPu",
                f"{topology.busbar_section_id}_Upu_value",
            ),
            (
                "lackOfVoltageRelay_UPhaseMonitoredBus",
                f"{topology.busbar_section_id}_phi_value",
            ),
            (
                "lackOfVoltageRelay_UMonitoredEquipmentPu",
                f"@{topology.equipment_id}@@NODE"
                f"{topology.line_side}@_Upu_value",
            ),
            (
                "lackOfVoltageRelay_UPhaseMonitoredEquipment",
                f"@{topology.equipment_id}@@NODE"
                f"{topology.line_side}@_phi_value",
            ),
            (
                "lackOfVoltageRelay_switchControlSignal",
                f"{topology.switch_id}_state_value",
            ),
        )

        for var1, var2 in monitor_connections:
            self._add_dyd_connect(
                id1=lovr_id,
                var1=var1,
                id2=network_id,
                var2=var2,
            )

        for existing_lovr_id in existing_lovr_ids:
            self._add_dyd_connect(
                id1=lovr_id,
                var1="lackOfVoltageRelay_sleepMode",
                id2=existing_lovr_id,
                var2="lackOfVoltageRelay_sleepMode",
            )
