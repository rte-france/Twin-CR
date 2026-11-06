"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging

from handlers.xml_handler import XmlHandler
from handlers.dyd_handler import DydHandler
from handlers.iidm_handler import IIDMHandler
from utils import PAR_XSD_PATH
from pathlib import Path

logger = logging.getLogger(__name__)

class ParHandlerLoader:
    def __init__(self):
        self.par_handler_per_par_file: dict[str | Path, ParHandler] = {}

    def get_handler(self, par_file: str | Path):
        if par_file in self.par_handler_per_par_file:
            return self.par_handler_per_par_file[par_file]
        else:
            par_handler = ParHandler(par_file)
            self.par_handler_per_par_file[par_file] = par_handler
            return par_handler


class ParHandler(XmlHandler):
    if Path(PAR_XSD_PATH).is_file():
        XSD_FILE = PAR_XSD_PATH
    else:
        logger.warning(f"{PAR_XSD_PATH} does not exist, par validation will not be performed")

    def modify_par(self, set_id, par_name, par_value):
        par_list = self._tree.findall(f"set[@id='{set_id}']/par[@name='{par_name}']", namespaces=self._nsmap)
        if len(par_list) == 0:
            msg = f"Parameter {set_id}::{par_name} not found in {self._file}"
            logger.error(msg)
            raise RuntimeError(msg)
        if len(par_list) > 1:
            msg = f"Parameter {set_id}::{par_name} is not unique in {self._file}"
            logger.error(msg)
            raise RuntimeError(msg)
        logger.info(
            f"Parameter update: file: {self._file.name}, set id: {set_id} par name: {par_name}, value: {par_value}")
        par_list[0].attrib["value"] = str(par_value)

    def get_values(self, set_id):
        par_list = self._tree.findall(f"dyn:set[@id='{set_id}']/dyn:par", namespaces=self._nsmap)
        par_dict = {}
        for p in par_list:
            par_dict[p.attrib["name"]] = p.attrib["value"]
        return par_dict

    def get_reference(self, set_id: str, par_id: str):
        reference = self._tree.find(f"dyn:set[@id='{set_id}']/dyn:reference[@name='{par_id}']", namespaces=self._nsmap)
        if reference is None:
            raise ValueError(f"Parameter {par_id} not found in set {set_id}")
        return reference
