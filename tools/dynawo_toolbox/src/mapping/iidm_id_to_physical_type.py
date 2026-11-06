"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from lxml import etree

def get_xml_local_name(element):
    return etree.QName(element.tag).localname

PHYSICAL_TYPES = ["line",
                     "generator",
                     "twoWindingsTransformer",
                     "threeWindingsTransformer",
                     "substation",
                     "voltageLevel",
                     "busbarSection",
                     "switch",
                     "load",
                     "battery",
                     "shunt",
                     "staticVarCompensator",
                     "hvdcLine",
                     ]

def get_iidm_id_to_physical_type_map(iidm_file):
    iidm_id_to_physical_type = {}

    network_xml = etree.parse(iidm_file).getroot()
    for element in network_xml.xpath("//*"):
        id = element.get("id")
        physical_type = get_xml_local_name(element)

        if not id:
            continue  # Skip elements without id
        if get_xml_local_name(element) not in PHYSICAL_TYPES:
            continue

        if id in iidm_id_to_physical_type:
            print(f"Warning: multiple elements with same id '{id}'")
        iidm_id_to_physical_type[id] = physical_type

    return iidm_id_to_physical_type
