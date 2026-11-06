"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Creates an IIDM example of a 4 buses system from scratch
"""

import os
import sys
import toml

import logging as log
from typing import Dict
from lxml import etree

import pandas as pd
import pypowsybl as pp


class NetworkBuilder:
    """
    Create the network
    """
    def __init__(self, config: Dict):
        """
        Instantiates the network
        :param config:
        """
        self.log = log.getLogger(self.__class__.__name__)
        self.network = pp.network.create_empty("4bus")
        self.config = config

    def build(self):
        """
        Builds the 4 bus system
        """
        self.log.info("Create substations")
        conf_subs = self.config["substations"]
        substations = pd.DataFrame.from_records(index="id", data=[
            {"id": substation_id, "country": country}
            for substation_id, country in zip(conf_subs["id"], conf_subs["country"])
        ])
        self.network.create_substations(substations)

        self.log.info("Create voltage levels")
        conf_vl = self.config["voltage_levels"]
        voltage_levels = pd.DataFrame.from_records(index="id", data=[
            {
                "id": voltage_level_id, "substation_id": substation_id,
                "low_voltage_limit": conf_vl["low_voltage_limit"], "nominal_v": conf_vl["nominal_v"],
                "high_voltage_limit": conf_vl["high_voltage_limit"], "topology_kind": conf_vl["topology_kind"]
            }
            for voltage_level_id, substation_id in zip(conf_vl["id"], conf_vl["substation_id"])
        ])
        self.network.create_voltage_levels(voltage_levels)

        self.log.info("Create substations")
        conf_bus = self.config["buses"]
        buses = pd.DataFrame.from_records(index="id", data=[
            {"id": bus_id, "voltage_level_id": voltage_level_id}
            for bus_id, voltage_level_id in zip(conf_bus["id"], conf_bus["voltage_level_id"])
        ])
        self.network.create_buses(buses)

        self.log.info("Create loads")
        conf_load = self.config["loads"]
        loads = pd.DataFrame.from_records(index="id", data=[
            {"id": load_id, "voltage_level_id": voltage_level_id, "bus_id": bus_id, "p0": p0, "q0": q0}
            for load_id, voltage_level_id, bus_id, p0, q0 in zip(
                conf_load["id"], conf_load["voltage_level_id"], conf_load["bus_id"], conf_load["p0"], conf_load["q0"]
            )
        ])
        self.network.create_loads(loads)

        self.log.info("Create generators")
        conf_gen = self.config["generators"]
        generators = pd.DataFrame.from_records(index="id", data=[
            {
                "id": gen_id, "voltage_level_id": voltage_level_id, "bus_id": bus_id,
                "target_p": target_p, "max_p": max_p, "min_p": min_p, "target_v": target_v, "voltage_regulator_on": True
            }
            for gen_id, voltage_level_id, bus_id, target_p, max_p, min_p, target_v in zip(
                conf_gen["id"], conf_gen["voltage_level_id"], conf_gen["bus_id"],
                conf_gen["target_p"], conf_gen["max_p"], conf_gen["min_p"], conf_gen["target_v"]
            )
        ])
        self.network.create_generators(generators)

        reactive_limits = pd.DataFrame.from_records(index="id", data=[
            {
                "id": gen_id, "min_q": -(1-0.9**2)**0.5 * max_p, "max_q": (1-0.9**2)**0.5 * max_p
            }
            for gen_id, max_p in zip(
                conf_gen["id"], conf_gen["max_p"]
            )
        ])
        self.network.create_minmax_reactive_limits(reactive_limits)

        self.log.info("Create lines")
        conf_line = self.config["lines"]
        lines = pd.DataFrame.from_records(index="id", data=[
            {
                "id": line_id, "voltage_level1_id": voltage_level1_id, "bus1_id": bus1_id,
                "bus2_id": bus2_id, "voltage_level2_id": voltage_level2_id,
                "b1": b1, "b2": b2, "g1": g1, "g2": g2, "r": r, "x": x
            }
            for line_id, voltage_level1_id, bus1_id, voltage_level2_id, bus2_id, b1, b2, g1, g2, r, x in zip(
                conf_line["id"], conf_line["voltage_level1_id"], conf_line["bus1_id"],
                conf_line["voltage_level2_id"], conf_line["bus2_id"], conf_line["b1"], conf_line["b2"],
                conf_line["g1"], conf_line["g2"], conf_line["r"], conf_line["x"]
            )
        ])
        self.network.create_lines(lines)

        self.log.info("Create transformers")
        conf_tf = self.config["transformer"]
        transformers = pd.DataFrame.from_records(index="id", data=[
            {
                "id": conf_tf["id"], "voltage_level1_id": conf_tf["voltage_level1_id"], "bus1_id": conf_tf["bus1_id"],
                "voltage_level2_id": conf_tf["voltage_level2_id"], "bus2_id": conf_tf["bus2_id"], "b": conf_tf["b"],
                "g": conf_tf["g"], "r": conf_tf["r"], "x": conf_tf["x"], "rated_u1": 400, "rated_u2": 400
            }
        ])
        self.network.create_2_windings_transformers(transformers)

        self.log.info("Create phase tap changer")
        conf_pst = conf_tf["phase_tap_changer"]
        phase_tap_changers = pd.DataFrame.from_records(
            index="id", columns=["id", "target_deadband", "regulation_mode", "low_tap", "tap"],
            data=[
                (
                    conf_pst["id"], conf_pst["target_deadband"], conf_pst["regulation_mode"],
                    conf_pst["low_tap"], conf_pst["tap"]
                )
            ]
        )
        conf_steps = conf_tf["phase_tap_changer_steps"]
        phase_tap_changer_steps = pd.DataFrame.from_records(
            index="id", columns=["id", "b", "g", "r", "x", "rho", "alpha"], data=[
                (
                    conf_steps["id"], conf_steps["b"], conf_steps["g"], r, x, conf_steps["rho"], alpha
                )
                for r, x, alpha in zip(conf_steps["r"], conf_steps["x"], conf_steps["alpha"])
            ]
        )
        self.network.create_phase_tap_changers(phase_tap_changers, phase_tap_changer_steps)


if __name__ == "__main__":
    config = toml.load(os.path.join(os.path.split(os.path.abspath(__file__))[0], os.pardir, os.pardir, "data", "configuration_4bus.toml"))
    log.basicConfig(level=config["log_level"])
    output_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.pardir, "network.xiidm")
    export_parameters = {"iidm.export.xml.topology-level": "BUS_BREAKER", "iidm.export.xml.version": "1.4"}
    network_builder = NetworkBuilder(config)
    network_builder.build()

    lf_results = pp.loadflow.run_ac(network_builder.network)
    log.info(f"Load flow results {lf_results}")
    log.info(f"Dumping network under {output_file}")

    # Add source format (must be non-empty for Dynawo, but cannot be changed from pypowsybl)
    network_string = network_builder.network.dump_to_string('XIIDM', export_parameters)
    network_string = network_string.encode()
    root = etree.fromstring(network_string)
    root.set('sourceFormat', 'TOML')
    log.info(f"Dumping network under {output_file}")
    with open(output_file, 'wb') as doc:
        doc.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
