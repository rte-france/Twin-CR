"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from lxml import etree
import pypowsybl as pp
import pandas as pd
from mapping.iidm_id_to_physical_type import PHYSICAL_TYPES

def get_xml_local_name(element):
    return etree.QName(element.tag).localname

class SubstationFinder:
    """
    Helper class to find the substation_id associated with a given XML iidm element
    """
    def __init__(self, iidm_file: str):
        self.network = pp.network.load(iidm_file)
        self.lines = self.network.get_lines()
        self.hvdc_lines = self.network.get_hvdc_lines()
        self.vls = self.network.get_voltage_levels()
        self.converter_stations = pd.concat([self.network.get_vsc_converter_stations(), self.network.get_lcc_converter_stations()])

        self.network_xml = etree.parse(iidm_file).getroot()

        self.elements_by_id : dict[str, etree._Element] = {}
        for element in self.network_xml.xpath("//*"):
            id = element.get("id")
            if id is None:
                continue
            if get_xml_local_name(element) not in PHYSICAL_TYPES:
                continue

            if id in self.elements_by_id:
                print(f"Warning: multiple elements with same id '{id}'")
            self.elements_by_id[element.get("id")] = element

    def find_substation_id(self, element_id, side = None):
        element = self.elements_by_id.get(element_id)
        if not element_id:
            raise RuntimeError("No element with id ", element_id)

        element_type = get_xml_local_name(element)
        if element_type == "line":
            if side == 1:
                vl_id = self.lines.at[element_id, "voltage_level1_id"]
            elif side == 2:
                vl_id = self.lines.at[element_id, "voltage_level2_id"]
            else:
                raise RuntimeError("side must be specified (either 1 or 2), for elements of type line")
            substation_id = self.vls.at[vl_id, "substation_id"]

        elif element_type == "hvdcLine":
            if side == 1:
                converter_id = self.hvdc_lines.at[element_id, "converter_station1_id"]
            elif side == 2:
                converter_id = self.hvdc_lines.at[element_id, "converter_station2_id"]
            else:
                raise RuntimeError("side must be specified (either 1 or 2), for elements of type hvdcLine")
            vl_id = self.converter_stations.at[converter_id, "voltage_level_id"]
            substation_id = self.vls.at[vl_id, "substation_id"]

        elif element_type == 'substation':
            return element_id
        else:
            # substation_id = element.xpath("ancestor::iidm:substation[1]", namespaces=self.iidm_namespace)[0].get("id")
            parent = element.getparent()
            while True:
                if parent is None:
                    raise RuntimeError(element_type, element_id, "has no parent of type substation")
                if get_xml_local_name(parent) == "substation":
                    substation_id = parent.get("id")
                    break
                parent = parent.getparent()

        if substation_id:
            return substation_id
        else:
            raise RuntimeError("Substation id not found for", element_type, element_id)
