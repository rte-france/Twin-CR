"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from abc import ABC
import os
from pathlib import Path
from lxml import etree

class XmlHandler(ABC):

    XSD_FILE = None

    def __init__(self, xml_file: Path):

        if not os.path.isfile(xml_file):
            raise FileExistsError(f"XML file {xml_file} does not exist")

        self._file: Path = Path(xml_file)

        if self.XSD_FILE is None:
            parser = etree.XMLParser()
        else:
            schema_root = etree.parse(self.XSD_FILE)
            schema = etree.XMLSchema(schema_root)

            parser = etree.XMLParser(schema = schema)

        self._tree = etree.parse(self._file, parser=parser)
        self._nsmap = self._tree.getroot().nsmap
        if None in self._nsmap: del self._nsmap[None]
        self._nsmap["dyn"] = "http://www.rte-france.com/dynawo" # For RTE exported cases where "dyn" is None

    def flush_to_file(self):
        self._tree.write(self._file)

    def get_path(self):
        return self._file
