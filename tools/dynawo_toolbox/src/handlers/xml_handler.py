"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from abc import ABC
import lzma
import os
from pathlib import Path
from lxml import etree
import zstandard


def _parse(xml_file: Path, parser: etree.XMLParser) -> etree._ElementTree:
    """Parse an XML file that may be xz or zstd compressed (lxml itself only reads gzip)."""
    name = str(xml_file).lower()
    if name.endswith(".xz"):
        with lzma.open(xml_file) as stream:
            return etree.parse(stream, parser=parser)
    if name.endswith(".zst"):
        with open(xml_file, "rb") as compressed:
            with zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
                return etree.parse(stream, parser=parser)
    return etree.parse(xml_file, parser=parser)

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

        self._tree = _parse(self._file, parser)
        self._nsmap = self._tree.getroot().nsmap
        if None in self._nsmap: del self._nsmap[None]
        self._nsmap["dyn"] = "http://www.rte-france.com/dynawo" # For RTE exported cases where "dyn" is None

    def flush_to_file(self):
        if self._file.suffix.lower() in (".xz", ".zst"):
            raise ValueError(f"Cannot write back to the compressed XML file {self._file}")
        self._tree.write(self._file)

    def get_path(self):
        return self._file
