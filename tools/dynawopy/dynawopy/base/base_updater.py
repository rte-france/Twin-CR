"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from lxml import etree
from io import StringIO, BytesIO
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
from collections.abc import Iterable

from dynawopy.base.utils import bfs_nearest

class TestcaseUpdater_Base:
    __test__ = False
    def __init__(self, testcase):
        self.testcase = testcase

    def xp_iidm(self, expr):
        return self.testcase.xp_iidm(expr)

    def xp_crv(self, expr):
        return self.testcase.xp_crv(expr)

    def xp_dyd(self, expr):
        return self.testcase.xp_dyd(expr)

    def xp_jobs(self, expr):
        return self.testcase.xp_jobs(expr)

    def xp_par(self, expr):
        return self.testcase.xp_par(expr)

    def xpath(self, expr, tree):
        return self.testcase.xpath(expr, tree)

    def save(self, name=None, directory=None):
        self.testcase.save(name, directory)

    def _invalidate_iidm_cache(self):
        self._iidm_index = None
        self._vl_graph_cache.clear()

    def _ensure_iidm_index(self):
        if self._iidm_index is not None:
            return

        iidm_ns = self.testcase.nsmap["iidm"]
        iidm_tag = f"{{{iidm_ns}}}"
        substation_tag = f"{iidm_tag}substation"

        voltage_levels = {}
        substation_by_voltage_level = {}

        busbar_sections_by_id = {}
        voltage_level_by_busbar_section = {}
        busbar_sections_by_substation = defaultdict(set)

        switches_by_id = {}
        switches_by_name = defaultdict(list)
        voltage_level_by_switch_id = {}
        breakers_by_voltage_level_node = defaultdict(lambda: defaultdict(list))

        for voltage_level in self.xp_iidm("//iidm:voltageLevel"):
            voltage_level_id = voltage_level.get("id")
            if voltage_level_id is None:
                continue

            voltage_levels[voltage_level_id] = voltage_level

            parent = voltage_level.getparent()
            while parent is not None and parent.tag != substation_tag:
                parent = parent.getparent()

            substation_id = parent.get("id") if parent is not None else None
            if substation_id is not None:
                substation_by_voltage_level[voltage_level_id] = substation_id

            for busbar_section in voltage_level.iter(f"{iidm_tag}busbarSection"):
                busbar_section_id = busbar_section.get("id")
                if busbar_section_id is None:
                    continue

                busbar_sections_by_id[busbar_section_id] = busbar_section
                voltage_level_by_busbar_section[
                    busbar_section_id
                ] = voltage_level_id

                if substation_id is not None:
                    busbar_sections_by_substation[substation_id].add(
                        busbar_section_id
                    )

            for switch in voltage_level.iter(f"{iidm_tag}switch"):
                switch_id = switch.get("id")
                switch_name = switch.get("name")

                if switch_id is not None:
                    switches_by_id[switch_id] = switch
                    voltage_level_by_switch_id[switch_id] = voltage_level_id

                if switch_name is not None:
                    switches_by_name[switch_name].append(switch)

                if switch.get("kind") == "BREAKER":
                    for node in {switch.get("node1"), switch.get("node2")}:
                        if node is not None:
                            breakers_by_voltage_level_node[
                                voltage_level_id
                            ][node].append(switch)

        lines_by_id = {}
        lines_by_voltage_level = defaultdict(list)
        lines_by_substation = defaultdict(list)

        for line in self.xp_iidm("//iidm:line"):
            line_id = line.get("id")
            if line_id is not None:
                lines_by_id[line_id] = line

            seen_substations = set()

            for side in (1, 2):
                voltage_level_id = line.get(f"voltageLevelId{side}")
                node = line.get(f"node{side}")

                if voltage_level_id is None:
                    continue

                if node is not None:
                    lines_by_voltage_level[voltage_level_id].append(
                        (node, line)
                    )

                substation_id = substation_by_voltage_level.get(
                    voltage_level_id
                )

                if (
                    substation_id is not None
                    and substation_id not in seen_substations
                ):
                    lines_by_substation[substation_id].append(
                        (
                            line_id,
                            f"node{side}",
                            node,
                            voltage_level_id,
                        )
                    )
                    seen_substations.add(substation_id)

        self._iidm_index = {
            "voltage_levels": voltage_levels,
            "substation_by_voltage_level": substation_by_voltage_level,
            "busbar_sections_by_id": busbar_sections_by_id,
            "voltage_level_by_busbar_section": (
                voltage_level_by_busbar_section
            ),
            "busbar_sections_by_substation": {
                substation_id: frozenset(busbar_ids)
                for substation_id, busbar_ids in (
                    busbar_sections_by_substation.items()
                )
            },
            "switches_by_id": switches_by_id,
            "switches_by_name": {
                switch_name: tuple(switches)
                for switch_name, switches in switches_by_name.items()
            },
            "voltage_level_by_switch_id": voltage_level_by_switch_id,
            "breakers_by_voltage_level_node": {
                voltage_level_id: {
                    node: tuple(switches)
                    for node, switches in nodes.items()
                }
                for voltage_level_id, nodes in (
                    breakers_by_voltage_level_node.items()
                )
            },
            "lines_by_id": lines_by_id,
            "lines_by_voltage_level": lines_by_voltage_level,
            "lines_by_substation": lines_by_substation,
        }

    def _build_vl_graph(self, voltagelevel_id):
        self._ensure_iidm_index()

        cached = self._vl_graph_cache.get(voltagelevel_id)
        if cached is not None:
            return cached

        voltage_level = self._iidm_index["voltage_levels"].get(voltagelevel_id)
        if voltage_level is None:
            raise ValueError(f"Unknown voltage level '{voltagelevel_id}'")

        iidm_tag = f"{{{self.testcase.nsmap['iidm']}}}"

        graph = defaultdict(set)
        busbar_section_node_map = {}
        line_node_map = {}
        breaker_node_map = {}

        for switch in voltage_level.iter(f"{iidm_tag}switch"):
            node1 = switch.get("node1")
            node2 = switch.get("node2")

            if node1 is None or node2 is None:
                continue

            graph[node1].add(node2)
            graph[node2].add(node1)

            if switch.get("kind") == "BREAKER":
                breaker_node_map[(node1, node2)] = switch

        for busbar_section in voltage_level.iter(f"{iidm_tag}busbarSection"):
            node = busbar_section.get("node")
            if node is not None:
                busbar_section_node_map[node] = busbar_section

        for node, line in self._iidm_index["lines_by_voltage_level"].get(
            voltagelevel_id, ()
        ):
            line_node_map[node] = line

        result = (
            graph,
            busbar_section_node_map,
            line_node_map,
            breaker_node_map,
        )
        self._vl_graph_cache[voltagelevel_id] = result

        return result

    def _find_bus_and_equipment_from_switch(self, switch, vl_graph=None):
        voltage_level_id = self._get_voltage_level_id_for_switch(switch)

        node1 = switch.get("node1")
        node2 = switch.get("node2")

        if node1 is None or node2 is None:
            raise ValueError(
                f"Switch '{switch.get('id')}' must have node1 and node2."
            )

        (
            graph,
            busbar_section_node_map,
            line_node_map,
            _,
        ) = (
            vl_graph
            if vl_graph is not None
            else self._build_vl_graph(voltage_level_id)
        )

        # Keep the original node1 -> busbar / node2 -> line preference,
        # but support XML files with the switch orientation reversed.
        for busbar_start_node, line_start_node in (
            (node1, node2),
            (node2, node1),
        ):
            busbar_section = bfs_nearest(
                start_node=busbar_start_node,
                graph=graph,
                blocked_node=line_start_node,
                target_node_map=busbar_section_node_map,
            )

            line = bfs_nearest(
                start_node=line_start_node,
                graph=graph,
                blocked_node=busbar_start_node,
                target_node_map=line_node_map,
            )

            if busbar_section is not None and line is not None:
                return line, busbar_section

        switch_label = switch.get("id") or switch.get("name") or "<unnamed>"
        raise ValueError(
            f"Could not find both a line and a busbar section for switch "
            f"'{switch_label}'."
        )

    def _get_lines_connected_to_substation(self, substation_id):
        self._ensure_iidm_index()

        lines = self._iidm_index["lines_by_substation"].get(substation_id, ())
        if not lines:
            raise ValueError(
                f"Found no connected lines for substation {substation_id}"
            )

        return list(lines)

    def _get_cached_object(self, id_or_name: str, obj_type: str, selector: callable = None):
        self._ensure_iidm_index()
        selector = selector if selector is not None else lambda x: True

        if id_or_name is None:
            raise ValueError("id must not be None.")

        obj = self._iidm_index.get(f"{obj_type}_by_id", {}).get(id_or_name)
        if obj is not None:
            return obj

        matches = tuple(
            obj
            for obj in self._iidm_index.get(f"{obj_type}_by_name", {}).get(
                id_or_name,
                (),
            )
            if selector(obj)
        )

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            raise ValueError(
                f"{obj_type} name '{id_or_name}' is ambiguous. "
                f"Use the {obj_type} id instead."
            )

        raise ValueError(
            f"Unknown {obj_type} id or name '{id_or_name}'."
        )

    def _get_cached_line(self, line_id_or_name):
        return self._get_cached_object(line_id_or_name, "lines")

    def _get_cached_busbar_section(self, busbar_section_id):
        return self._get_cached_object(busbar_section_id, "busbar_sections")

    def _get_cached_breaker_by_name(self, switch_name: str):
        """Return exactly one BREAKER matched by its IIDM @name."""
        return self._get_cached_object(switch_name, "switches", lambda x: x.get("kind") == "BREAKER")

    def _get_cached_switch(self, switch_id_or_name: str):
        return self._get_cached_object(switch_id_or_name, "switches")

    def _get_voltage_level_id_for_switch(self, switch):
        self._ensure_iidm_index()

        switch_id = switch.get("id")
        if switch_id is not None:
            voltage_level_id = self._iidm_index[
                "voltage_level_by_switch_id"
            ].get(switch_id)

            if voltage_level_id is not None:
                return voltage_level_id

        voltage_level_tag = (
            f"{{{self.testcase.nsmap['iidm']}}}voltageLevel"
        )

        parent = switch.getparent()
        while parent is not None:
            if parent.tag == voltage_level_tag:
                voltage_level_id = parent.get("id")
                if voltage_level_id is not None:
                    return voltage_level_id

            parent = parent.getparent()

        switch_label = switch_id or switch.get("name") or "<unnamed>"
        raise ValueError(
            f"Could not determine the voltage level of switch "
            f"'{switch_label}'."
        )

    def _resolve_voltagelevel_id(self, voltagelevel):
        if voltagelevel is None:
            return None

        if isinstance(voltagelevel, str):
            voltage_level_id = voltagelevel
        else:
            try:
                voltage_level_id = voltagelevel.get("id")
            except AttributeError as exc:
                raise TypeError(
                    "voltagelevel must be a voltage-level id or an XML element."
                ) from exc

        self._ensure_iidm_index()

        if voltage_level_id not in self._iidm_index["voltage_levels"]:
            raise ValueError(
                f"Unknown voltage level '{voltage_level_id}'."
            )

        return voltage_level_id

    @staticmethod
    def _normalize_line_side(line_side):
        if (
            isinstance(line_side, int)
            and not isinstance(line_side, bool)
            and line_side in (1, 2)
        ):
            return line_side

        if isinstance(line_side, str):
            value = line_side.strip().lower()

            if value.startswith("node"):
                value = value[4:]

            if value in {"1", "2"}:
                return int(value)

        raise ValueError(
            "line_side must be 1, 2, 'node1', or 'node2'."
        )

    @staticmethod
    def _line_side_for_voltage_level(line, voltage_level_id):
        matching_sides = [
            side
            for side in (1, 2)
            if line.get(f"voltageLevelId{side}") == voltage_level_id
        ]

        if len(matching_sides) == 1:
            return matching_sides[0]

        line_id = line.get("id")

        if not matching_sides:
            raise ValueError(
                f"Line '{line_id}' is not connected to voltage level "
                f"'{voltage_level_id}'."
            )

        raise ValueError(
            f"Line '{line_id}' is connected twice to voltage level "
            f"'{voltage_level_id}'. Specify line_side explicitly."
        )

    def _get_direct_breaker_for_line_side(
        self,
        line,
        line_side,
        voltage_level_id,
    ):
        line_node = line.get(f"node{line_side}")
        if line_node is None:
            raise ValueError(
                f"Line '{line.get('id')}' has no node{line_side}."
            )

        self._ensure_iidm_index()

        breakers_by_node = self._iidm_index[
            "breakers_by_voltage_level_node"
        ].get(voltage_level_id, {})

        matches = breakers_by_node.get(line_node, ())

        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one breaker adjacent to line "
                f"'{line.get('id')}' at node '{line_node}' in voltage "
                f"level '{voltage_level_id}', found {len(matches)}."
            )

        return matches[0]

    def _get_connected_elements(self, bus_id):
        return self.xp_iidm(
            f"//*[@connectableBus='{bus_id}'] | //*[@connectableBus1='{bus_id}'] | //*[@connectableBus2='{bus_id}']",
        )

    def _add_dyd_connect(self, id1: str, var1: str, id2: str, var2: str):
        """Add a <dyn:connect> element to the DYD tree."""
        dyn_ns = self.testcase.nsmap["dyn"]
        dyd_root = self.testcase.dyd.getroot()

        etree.SubElement(
            dyd_root,
            f"{{{dyn_ns}}}connect",
            attrib={
                "id1": id1,
                "var1": var1,
                "id2": id2,
                "var2": var2,
            },
        )

    def _insert_blackboxmodel(self, model_id: str, lib: str, parId: str = None, parFile: str = None):
        """Insert blackBoxModel element into the DYD tree."""
        dyn_ns = self.testcase.nsmap["dyn"]
        dyd_root = self.testcase.dyd.getroot()

        etree.SubElement(
            dyd_root,
            f"{{{dyn_ns}}}blackBoxModel",
            attrib={
                "id": model_id,
                "lib": lib,
                "parFile": parFile if parFile is not None else f"{self.testcase.name}.par",
                "parId": parId if parId is not None else model_id,
            },
        )
