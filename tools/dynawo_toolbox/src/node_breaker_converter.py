"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
from collections import defaultdict
import re

import pypowsybl as pp
from lxml import etree


def convert_network(n: pp.network.Network):
    """
    Convert a bus-breaker network in a node-breaker one.
    Ideally, this would use network.update_voltage_levels(id=vl_id, topology_kind='NODE_BREAKER') but this functionnality does not exist.
    So, we do some weird xml shenanigans.
    """
    xml = n.dump_to_string(parameters={"iidm.export.xml.version" : "1.4"})
    XMLparser = etree.XMLParser(remove_blank_text=True)  # Necessary for pretty_print to work
    root = etree.fromstring(xml.encode(), parser=XMLparser)

    nsmap = root.nsmap
    iidm_ns = nsmap.get(None) or nsmap.get("iidm")
    iidm = f"{{{iidm_ns}}}"

    # Generate bus_id to node mapping
    buses = n.get_bus_breaker_view_buses()
    bus_id_2_node: dict[str, int] = {}
    node_counter = defaultdict(int)

    for bus_id, bus in buses.iterrows():
        vl = bus["voltage_level_id"]

        node = node_counter[vl]
        bus_id_2_node[bus_id] = node
        node_counter[vl] = node + 1

    # Convert all voltage levels to NODE_BREAKER and convert buses to busbarSections
    for vl in root.findall(f".//{iidm}voltageLevel"):
        topology_kind = vl.get("topologyKind")
        if topology_kind == "BUS_BREAKER":
            vl.set("topologyKind", "NODE_BREAKER")

            breaker_topology = vl.find(f"{iidm}busBreakerTopology")
            if breaker_topology is not None:
                vl.remove(breaker_topology)

            node_topology = etree.SubElement(vl, f"{iidm}nodeBreakerTopology")

            for bus in breaker_topology.findall(f"{iidm}bus"):
                bus_id = bus.get("id")
                node = str(bus_id_2_node.get(bus_id, 0))
                etree.SubElement(node_topology, f"{iidm}busbarSection", id=bus_id, node=node)


    # Update all connectable elements' bus references to node references and add breakers everywhere
    BUS_ATTR_RE = re.compile(r"^bus(\d*)$")
    CONN_BUS_ATTR_RE = re.compile(r"^connectableBus(\d*)$")
    vls = {vl.get("id"): vl for vl in root.findall(f".//{iidm}voltageLevel")}

    for elem in root.iter():
        attrs = list(elem.attrib.keys())

        switches_data: dict[str, dict[str, str]] = {}
        for attr in attrs:
            # connectableBus -> assign node
            m = CONN_BUS_ATTR_RE.match(attr)
            if m:
                suffix = m.group(1)

                bus_id = elem.attrib.pop(attr)
                bus_node = bus_id_2_node[bus_id]

                # Voltage level is either specified as attribute (e.g. line) or as parent (e.g. generator)
                vl_id = elem.get(f"voltageLevelId{suffix}")
                if vl_id is None:
                    parent = elem.getparent()
                    while parent is not None:
                        if parent.tag.endswith("voltageLevel"):
                            vl_id = parent.get("id")
                            break
                        parent = parent.getparent()

                # Assign new node to element and associated disconnector
                disconnector_node = node_counter[vl_id]
                node_counter[vl_id] += 1
                elem_node = node_counter[vl_id]
                node_counter[vl_id] += 1

                node_attr = f"node{suffix}"
                elem.set(node_attr, str(elem_node))

                if suffix not in switches_data:
                    switches_data[suffix] = {}
                switches_data[suffix]["bus_node"] = str(bus_node)
                switches_data[suffix]["disconnector_node"] = str(disconnector_node)
                switches_data[suffix]["elem_node"] = str(elem_node)
                switches_data[suffix]["voltage_level_id"] = vl_id
                switches_data[suffix]["connected"] = switches_data[suffix].get("connected", False)

            # bus -> mark breaker closed
            m = BUS_ATTR_RE.match(attr)
            if m:
                suffix = m.group(1)
                if suffix not in switches_data:
                    switches_data[suffix] = {}
                switches_data[suffix]["connected"] = True

        # create connectable internal nodes + breakers
        for suffix, switch_data in switches_data.items():
            vl = vls[switch_data["voltage_level_id"]]
            topo = vl.find(f"{iidm}nodeBreakerTopology")

            etree.SubElement(
                topo,
                f"{iidm}switch",
                id = f"{elem.get('id')}_disconnector{suffix}",
                node1 = switch_data["bus_node"],
                node2 = switch_data["disconnector_node"],
                kind = "DISCONNECTOR",
                retained = "false",
                open = "false",
            )

            etree.SubElement(
                topo,
                f"{iidm}switch",
                id = f"{elem.get('id')}_breaker{suffix}",
                node1 = switch_data["disconnector_node"],
                node2 = switch_data["elem_node"],
                kind = "BREAKER",
                retained = "true",
                open = "false" if switch_data["connected"] == True else "true",
            )

    xml_str = etree.tostring(root, pretty_print = True, xml_declaration = True, encoding='UTF-8').decode()
    n_NB = pp.network.load_from_string("NodeBreakerNetwork.xiidm", xml_str)
    return n_NB


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert an iidm network from bus-breaker to node-breaker, adding disconnectors and breakers to all elements")
    parser.add_argument(
        "-i", "--input", type=str, required=True, help="Input network file"
    )
    parser.add_argument(
        "-o", "--output", type=str, required=True, help="Output network file"
    )
    args = parser.parse_args()

    n = pp.network.load(args.input)
    print("Pre-conversion load flow\n", pp.loadflow.run_ac(n))
    n_NB = convert_network(n)
    print("Post-conversion load flow\n", pp.loadflow.run_ac(n_NB))
    n_NB.save(args.output, parameters={"iidm.export.xml.version" : "1.4"})
