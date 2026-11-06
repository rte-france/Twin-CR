"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging
import pypowsybl as pp
import pandas as pd
from lxml import etree
from math import pi, sqrt

from handlers.xml_handler import XmlHandler

LimitsMap = dict[tuple[str, str], dict[int, float]]

logger = logging.getLogger(__name__)

class IIDMHandler(XmlHandler):
    XSD_FILE = None
    _network : pp.network.Network = None

    def __init__(self, xml_file):
        super().__init__(xml_file)
        self._network = pp.network.load(self._file)
        # self._id_map = {elem.get("id"):elem for elem in self._tree.getroot().xpath('//iidm:*[@id]', namespaces=self._nsmap) if "extension" not in elem.tag}
        self._id_map = {}
        for elem in self._tree.getroot().iter():
            if callable(elem.tag):   # filters out comments, PIs, entities
                continue
            if "extension" in elem.tag:
                continue
            elem_id = elem.get("id")
            if elem_id:
                self._id_map[elem_id] = elem

        self._elements: dict[str, pd.DataFrame] | None = None

    def get_components_with_tag(self, tag):
        return self._tree.getroot().xpath(f'iidm:{tag}', namespaces=self._nsmap)

    def get_component_with_id(self, iidm_id) -> etree._Element:
        return self._id_map.get(iidm_id)

    def get_id_list(self):
        return list(self._id_map.keys())

    def get_identifiable_tag_list(self):
        return set(e.tag for e in self._id_map.values())

    def load_elements(self):
        """
        Load network elements by xml tag
        """
        self._elements = {}
        element_getters = {
            "twoWindingsTransformer": self._network.get_2_windings_transformers,
            "threeWindingsTransformer": self._network.get_3_windings_transformers,
            "battery": self._network.get_batteries,
            "busbarSection": self._network.get_busbar_sections,
            "bus": self._network.get_buses,
            "generator": self._network.get_generators,
            "hvdcLine": self._network.get_hvdc_lines,
            "line": self._network.get_lines,
            "load": self._network.get_loads,
            "shunt": self._network.get_shunt_compensators,
            "staticVarCompensator": self._network.get_static_var_compensators,
            "substation": self._network.get_substations,
            "switch": self._network.get_switches,
            "voltageLevel": self._network.get_voltage_levels,
            "lccConverterStation": self._network.get_lcc_converter_stations,
            "vscConverterStation": self._network.get_vsc_converter_stations
        }
        for element_type in element_getters:
            self._elements[element_type] = element_getters[element_type]()

    def get_element_bus_id(self, iidm_id: str, side: int | None) -> str:
        if self._elements is None:
            self.load_elements()

        xml_element = self.get_component_with_id(iidm_id)
        element_type = etree.QName(xml_element).localname  # Get tag without namespace

        if element_type == "bus":
            return iidm_id
        else:
            if side is None:
                key = "bus_id"
            else:
                key = f"bus{side}_id"
            return self._elements[element_type].at[iidm_id, key]

    def get_element_voltage_level_id(self, iidm_id: str, side: int | None) -> str:
        if self._elements is None:
            self.load_elements()

        xml_element = self.get_component_with_id(iidm_id)
        element_type = etree.QName(xml_element).localname

        if element_type == "voltageLevel":
            return iidm_id
        else:
            if side is None:
                key = "voltage_level_id"
            else:
                key = f"voltage_level{side}_id"
            return self._elements[element_type].at[iidm_id, key]

    def get_element_voltage(self, iidm_id: str, side: int | None = None) -> float:
        bus_id = self.get_element_bus_id(iidm_id, side)
        return self._elements["bus"].at[bus_id, "v_mag"]

    def get_element_nominal_voltage(self, iidm_id: str, side: int | None = None) -> float:
        voltage_level_id = self.get_element_voltage_level_id(iidm_id, side)
        return self._elements["voltageLevel"].at[voltage_level_id, "nominal_v"]

    def get_element_voltage_pu(self, iidm_id: str, side: int | None = None) -> float:
        return self.get_element_voltage(iidm_id, side) / self.get_element_nominal_voltage(iidm_id, side)

    def get_element_angle(self, iidm_id: str, side: int | None = None) -> float:
        bus_id = self.get_element_bus_id(iidm_id, side)
        return self._elements["bus"].at[bus_id, "v_angle"]

    def get_element_angle_pu(self, iidm_id: str, side: int | None = None) -> float:
        return self.get_element_angle(iidm_id, side) * pi / 180

    def get_element_key(self, iidm_id: str, key: str):
        if self._elements is None:
            self.load_elements()

        xml_element = self.get_component_with_id(iidm_id)
        element_type = etree.QName(xml_element).localname
        if key in self._elements[element_type].keys():
            return self._elements[element_type].at[iidm_id, key]
        else:
            raise ValueError(f"Key {key} is not defined for element {iidm_id} of type {element_type}")

    def get_element_active_power(self, iidm_id: str, side: int | None = None) -> float:
        if side is None:
            key = "p"
        else:
            key = f"p{side}"
        return self.get_element_key(iidm_id, key)

    def get_element_active_power_pu(self, iidm_id: str, side: int | None = None) -> float:
        return self.get_element_active_power(iidm_id, side) / 100

    def get_element_reactive_power(self, iidm_id: str, side: int | None = None) -> float:
        if side is None:
            key = "q"
        else:
            key = f"q{side}"
        return self.get_element_key(iidm_id, key)

    def get_element_reactive_power_pu(self, iidm_id: str, side: int | None = None) -> float:
        return self.get_element_reactive_power(iidm_id, side) / 100

    def get_element_p_max(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "max_p")

    def get_element_p_max_pu(self, iidm_id: str) -> float:
        return self.get_element_p_max(iidm_id) / 100

    def get_element_q_max(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "max_q")

    def get_element_q_max_pu(self, iidm_id: str) -> float:
        return self.get_element_q_max(iidm_id) / 100

    def get_element_p_min(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "min_p")

    def get_element_p_min_pu(self, iidm_id: str) -> float:
        return self.get_element_p_min(iidm_id) / 100

    def get_element_q_min(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "min_q")

    def get_element_q_min_pu(self, iidm_id: str) -> float:
        return self.get_element_q_min(iidm_id) / 100

    def get_element_s_nom(self, iidm_id: str) -> float:
        try:
            p_max = self.get_element_p_max(iidm_id)
        except ValueError:
            p_max = None
        try:
            q_max = self.get_element_p_max(iidm_id)
        except ValueError:
            q_max = None

        if p_max is None and q_max is None:
            ValueError(f"SNom is not defined for element {iidm_id} of type {etree.QName(self.get_component_with_id(iidm_id)).localname}")

        # Replace None and NaN by zero
        p_max = 0 if pd.isna(p_max) else p_max
        q_max = 0 if pd.isna(q_max) else q_max

        return sqrt(p_max**2 + q_max**2)

    def get_element_s_nom_pu(self, iidm_id: str) -> float:
        return self.get_element_s_nom(iidm_id) / 100

    def get_element_target_p(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "target_p")

    def get_element_target_p_pu(self, iidm_id: str) -> float:
        return self.get_element_target_p(iidm_id) / 100

    def get_element_target_q(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "target_q")

    def get_element_target_q_pu(self, iidm_id: str) -> float:
        return self.get_element_target_q(iidm_id) / 100

    def get_element_target_u(self, iidm_id: str) -> float:
        return self.get_element_key(iidm_id, "target_p")

    def get_element_target_u_pu(self, iidm_id: str) -> float:
        return self.get_element_target_u(iidm_id) / self.get_element_nominal_voltage(iidm_id)

    def resolve_reference(self, orig_name: str, static_id: str, side: int | None = None):
        if orig_name in ["v", "uc"]:
            return self.get_element_voltage(static_id, side)
        if orig_name in ["v_pu", "uc_pu"]:
            return self.get_element_voltage_pu(static_id, side)
        if orig_name == "vNom":
            return self.get_element_nominal_voltage(static_id, side)
        if orig_name == "angle":
            return self.get_element_angle(static_id, side)
        if orig_name == "angle_pu":
            return self.get_element_angle_pu(static_id, side)
        if orig_name == "p":
            return self.get_element_active_power(static_id)
        if orig_name == "p_pu":
            return self.get_element_active_power_pu(static_id)
        if orig_name == "q":
            return self.get_element_reactive_power(static_id)
        if orig_name == "q_pu":
            return self.get_element_reactive_power_pu(static_id)
        if orig_name == "pMax":
            return self.get_element_p_max(static_id)
        if orig_name == "pMax_pu":
            return self.get_element_p_max_pu(static_id)
        if orig_name == "qMax":
            return self.get_element_q_max(static_id)
        if orig_name == "qMax_pu":
            return self.get_element_q_max_pu(static_id)
        if orig_name == "pMin":
            return self.get_element_p_min(static_id)
        if orig_name == "pMin_pu":
            return self.get_element_p_min_pu(static_id)
        if orig_name == "qMin":
            return self.get_element_q_min(static_id)
        if orig_name == "qMin_pu":
            return self.get_element_q_min_pu(static_id)
        if orig_name == "SNom":
            return self.get_element_s_nom(static_id)
        if orig_name == "targetV":
            return self.get_element_target_u(static_id)
        if orig_name == "targetV_pu":
            return self.get_element_target_u_pu(static_id)
        if orig_name == "targetP":
            return self.get_element_target_p(static_id)
        if orig_name == "targetP_pu":
            return self.get_element_target_p_pu(static_id)
        if orig_name == "targetQ":
            return self.get_element_target_q(static_id)
        if orig_name == "targetQ_pu":
            return self.get_element_target_q_pu(static_id)
        raise NotImplementedError(f"Unknown origName {orig_name} in reference")

    def build_current_limits_map(self) -> LimitsMap:
        """
        Extract current-limit "arming" thresholds using pypowsybl's get_operational_limits().

        For each (element_id, side), temporary limits are sorted from longest
        acceptable duration to shortest; the arming value for a tier is the
        previous (less restrictive) tier's value, starting from the permanent
        limit (acceptable_duration == -1).

        E.g.
        <iidm:currentLimits2 permanentLimit="1291">
            <iidm:temporaryLimit name="IT20" acceptableDuration="1200" value="1645"/>
            <iidm:temporaryLimit name="IT5" acceptableDuration="300" value="2393"/>
            <iidm:temporaryLimit name="IT" acceptableDuration="1"/>
        </iidm:currentLimits2>
        would return
        {
            1200: 1291,
            300: 1645,
            1: 2393
        }
        """
        df = self._network.get_operational_limits().reset_index()
        df = df[df['type'] == 'CURRENT']

        limits_map: LimitsMap = {}
        for (element_id, side), group in df.groupby(['element_id', 'side']):
            group = group.sort_values('acceptable_duration', ascending=False)

            permanent = group[group['acceptable_duration'] == -1]
            if permanent.empty:  # temporary limits alone give no threshold to attach them to
                continue
            prev_value = float(permanent['value'].iloc[0])

            entries: dict[int, float] = {}
            for _, row in group[group['acceptable_duration'] != -1].iterrows():
                entries[int(row['acceptable_duration'])] = prev_value
                prev_value = float(row['value'])

            limits_map[(element_id, side)] = entries

        return limits_map
