"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json

import logging
from pathlib import Path
import sys

from json_io import load_json
from mapping.iidm_id_to_physical_type import get_iidm_id_to_physical_type_map


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class TiMapped:
    def __init__(self, data: dict[str, str], iidm_id_to_physical_type: dict[str, str]):
        self.data = data
        self.iidm_id_to_physical_type = iidm_id_to_physical_type

    def get_type(self):
        """
        Return TM, TS, TC, TVC, etc.
        """
        return self.data["type"]

    def get_tase2(self):
        return self.data.get("tase2")

    def get_rtu(self):
        rtu = self.data.get("ru")
        if rtu is None:
            if self.get_type() in ["TM", "TS", "TC", "TVC"]:
                logger.debug(f"No RTU set in {self.data}")
        return rtu

    def get_iidm_id(self):
        if self._is_breaker_status():
            switch_id = self.data.get("iidmdj")
            if switch_id and self.iidm_id_to_physical_type.get(switch_id) == "switch":
                return switch_id
            logger.debug(f"No switch iidmdj in {self.data}")
            return None
        iidm_id = self.data.get("iidm")
        if iidm_id is None:  # Either "iidm" field not present or set as null
            iidm_id = self.data.get("bayiidm")
        if iidm_id is None:
            logger.debug(f"No iidm set in {self.data}")
        return iidm_id

    def get_label(self):
        label = self.data["libelle"]
        if self.data.get("iidm") and self.get_type() == "TM":
            label = self.data["old_lib"]
        return label

    def get_titien_label(self):
        if self.get_type() == "TS":
            return self.data["dname"]  # rsname in older versions
        else:
            return self.get_label()

    def get_attribute(self):
        """
        Return P, Q, U, or state
        Note: for the Dynawo mapping, the attribute (+ side if any) must be included in the rules in ../configurator/output_rules.yaml
        (for TM/TS) or in ../configurator/input_rules.yaml (for TC/TVC)
        """
        if self._is_breaker_status():
            return "state"

        attribute = self.data.get("typ")
        if attribute in [None, ""]:
            return None

        attribute = attribute.upper()
        if attribute in ["U", "U.BTS"]:
            return "U"
        if attribute in ["P"]:
            return "P"
        if attribute in ["Q"]:
            return "Q"
        if attribute in ["STATE"]:
            return "state"

        logger.debug(f"Unhandled attribute {attribute} in {self.data}")  # Currently very verbose
        return None

    def get_physical_type(self):
        iidm_id = self.get_iidm_id()
        if iidm_id is None:
            return None

        physical_type = self.iidm_id_to_physical_type.get(iidm_id)
        if physical_type is None:
            logger.info(f"{iidm_id} not found in IIDM file (from {self.data})")
            return None
        return physical_type

    def get_side(self):
        """
        Return which side of the elements the ti refers to (1, 2, or 3)
        Return "" if the side has no meaning (i.e. for all elements excepts lines and transformer, and for attributes that do not depend on the side (e.g. state))
        Return None if not specified, or if the physical type or attribute is not defined
        """
        attribute = self.get_attribute()
        physical_type = self.get_physical_type()
        if physical_type is None or attribute is None:
            logger.debug(f"Attribute and physical_type needed to find side (for {self.data})")
            return None

        if physical_type in ["line", "twoWindingsTransformer", "threeWindingsTransformer", "hvdcLine"] and attribute in ["P", "Q"]:  # Side does not need to be specified for state
            side = self.data.get("side")
            if side is None:
                logger.debug(f"Side not found for {self.data}")
                return None
            side = int(side)

            valid_sides = [1, 2]
            if physical_type == "threeWindingsTransformer":
                valid_sides.append(3)

            if side in valid_sides:
                return side
            else:
                logger.info(f"Invalid side {side} for element of type {physical_type} (from {self.data})")
                return None
        else:
            return ""  # Side has no meaning / is not needed

    def get_iidm_key(self):
        """
        Return iidm_id + ":" + attribute (+ side if relevant)
        Note: for the Dynawo mapping, the attribute (+ side if any) must be included in the rules in ../configurator/output_rules.yaml
        (for TM/TS) or in ../configurator/input_rules.yaml (for TC/TVC)
        """
        iidm_id = self.get_iidm_id()
        attribute = self.get_attribute()
        side = self.get_side()

        if iidm_id is None or attribute is None or side is None:
            return None

        return iidm_id + ":" + attribute + str(side)

    def _is_breaker_status(self):
        if self.data.get("bayt") in ["Breaker", "Disconnector", "LoadBreakSwitch"]:
            if self.data.get("pointclass") in ["SA.AT#", "S.SHUNTb", "SI.#", "SA.b#HT", "DJ#.HT", "DJ.TRu1#", "DJ.MT#", "SS.bt##", "SRB.##",
                                               "SA.AT#HT", "SL.HT", "DJ.GR.S", "DJ.COMP", "SA.b", "SRB#.HT", "SM.b", "SL#", "COUPL", "SSb.ssHT",
                                               "INTER2", "DJ", "DJ.MT#.S", "COUPL.S", "DJ.HT.S", "DJ.SH.HT", "INTER", "INTER1", "DJ.MT.GR",
                                               "SA.#HT", "DJ.MCOMP", "INTERbHT", "DJ.HT", "SA.b#", "DJ.TA", "DJ.GR"]:
                return True
        return False

class TiMapper:
    def __init__(self, iidm_file: str | Path, cyber_mapping_file: str | Path):
        self.timappeds: list[TiMapped] = []
        iidm_id_to_physical_type = get_iidm_id_to_physical_type_map(iidm_file)

        telecontrols = load_json(cyber_mapping_file)

        for telecontrol in telecontrols:
            self.timappeds.append(TiMapped(telecontrol, iidm_id_to_physical_type))
