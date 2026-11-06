"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging

from handlers.xml_handler import XmlHandler
from models.events import EVENT_CLASS
from utils import DYD_XSD_PATH
from pathlib import Path
from lxml import etree

logger = logging.getLogger(__name__)

class DydHandler(XmlHandler):
    if Path(DYD_XSD_PATH).is_file():
        XSD_FILE = DYD_XSD_PATH
    else:
        logger.warning(f"{DYD_XSD_PATH} does not exist, dyd validation will not be performed")

    def get_events(self):
        event_list = self._tree.getroot().xpath('dyn:blackBoxModel[starts-with(@lib, "Event")]', namespaces=self._nsmap)
        event_dict = {}
        for e in event_list:
            event_dict[e.attrib["id"]] = EVENT_CLASS[e.attrib["lib"]](e.attrib["id"], e.get("parId"))
        return event_dict

    def get_dynamic_models(self):
        return self._tree.getroot().xpath('dyn:blackBoxModel', namespaces=self._nsmap)

    def get_dynamic_models_with_par_id(self, par_id: str):
        return self._tree.getroot().xpath(f'dyn:blackBoxModel[@parId="{par_id}"]', namespaces=self._nsmap)

    def get_connections(self):
        return self._tree.getroot().xpath('dyn:connect', namespaces=self._nsmap)

    def get_all_resolved_connections(self):
        """
        Get all connections, with macroConnectors replaced by the equivalent individual connectors, and macros (@STATIC_ID@, @INDEX@, @NAME@) resolved
        """
        connections = self.get_connections()
        macro_connectors = self._tree.getroot().xpath('dyn:macroConnector', namespaces=self._nsmap)
        macro_connectors_by_id = {macro_connector.attrib["id"]: macro_connector for macro_connector in macro_connectors}
        macro_connections = self._tree.getroot().xpath('dyn:macroConnect', namespaces=self._nsmap)
        dyn_models_by_id = {dyn_model.attrib["id"]: dyn_model for dyn_model in self.get_dynamic_models()}

        for macro_connection in macro_connections:
            macro_connector = macro_connectors_by_id[macro_connection.attrib["connector"]]
            for connection in macro_connector:
                id1: str = macro_connection.attrib["id1"]
                id2: str = macro_connection.attrib["id2"]
                var1: str = connection.attrib["var1"]
                var2: str = connection.attrib["var2"]

                if macro_connector.get("index1") == "true":
                    var1, var2 = [var.replace("@INDEX@", macro_connection.attrib["index1"]) for var in [var1, var2]]

                if macro_connector.get("name2") == "true":
                    var1, var2 = [var.replace("@NAME@", macro_connection.attrib["name2"]) for var in [var1, var2]]

                if "@STATIC_ID@" in id1:
                    static_id = dyn_models_by_id[id1].attrib["staticId"]
                    id1.replace("@STATIC_ID@", static_id)
                if "@STATIC_ID@" in id2:
                    static_id = dyn_models_by_id[id2].attrib["staticId"]
                    id2.replace("@STATIC_ID@", static_id)

                resolved_connection = etree.Element("connect", nsmap=self._nsmap)
                resolved_connection.attrib["id1"] = id1
                resolved_connection.attrib["id2"] = id2
                resolved_connection.attrib["var1"] = var1
                resolved_connection.attrib["var2"] = var2
                connections.append(resolved_connection)
        return connections

    # def get_dynamic_models(self):
    #     return self._tree.getroot().xpath('dyn:blackBoxModel[@static_model]', namespaces=self._nsmap)
