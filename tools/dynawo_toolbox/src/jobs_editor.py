"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

"""
Reading and completing a Dynawo jobs file.

Dynawo accepts either a prefixed namespace (<dyn:job>) or a default one (<job
xmlns="...">), but not a mix, so anything inserted here follows whatever the
document already uses.

Every edit is idempotent: running it twice leaves the file unchanged.
"""

from pathlib import Path

import lxml.etree as ET

DYN_URI = "http://www.rte-france.com/dynawo"

# Fixed for a real-time run; only couplingTimeStep varies, and it has to match
# the orchestrator's master period.
ZMQ_INPUT_ENDPOINT = "tcp://*:5555"
ZMQ_OUTPUT_ENDPOINT = "tcp://*:5556"
STREAMS = (
    ("CURVES", "BYTES"),
    ("TIMELINE", "JSON"),
    ("CONSTRAINTS", "JSON"),
    ("DUMP", None),
)


def _local(tag) -> str:
    """Tag name without its namespace."""
    return ET.QName(tag).localname if isinstance(tag, str) and "}" in tag else str(tag)


def find_all(root, name: str):
    """Elements with this local name, whichever namespace convention is used."""
    return root.xpath(f"//*[local-name()='{name}']")


def find_one(root, name: str):
    found = find_all(root, name)
    return found[0] if found else None


class JobsFile:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        # Keeping the existing formatting matters: these files are hand-edited.
        self._tree = ET.parse(str(self.path))
        self._root = self._tree.getroot()
        # A prefixed document has a prefix on the root; a default-namespace one
        # does not. New elements are built to match.
        self._prefix = self._root.prefix
        self._uri = ET.QName(self._root).namespace

    def _tag(self, name: str) -> str:
        return f"{{{self._uri}}}{name}" if self._uri else name

    def _make(self, name: str, **attrib):
        return self._root.makeelement(self._tag(name), attrib)

    @property
    def namespace_style(self) -> str:
        return f"{self._prefix}:" if self._prefix else ("default" if self._uri else "none")

    def dyd_files(self) -> list[str]:
        """dydFile values in document order."""
        return [
            element.attrib["dydFile"]
            for element in find_all(self._root, "dynModels")
            if element.attrib.get("dydFile")
        ]

    def iidm_file(self) -> str | None:
        network = find_one(self._root, "network")
        return network.attrib.get("iidmFile") if network is not None else None

    def ensure_dyd(self, dyd_file: str) -> bool:
        """
        Add a <dynModels dydFile="..."/> for this file unless it is already
        referenced. Returns whether the document changed.
        """
        if dyd_file in self.dyd_files():
            return False

        modeler = find_one(self._root, "modeler")
        if modeler is None:
            raise ValueError(f"{self.path.name} has no <modeler> element")

        element = self._make("dynModels", dydFile=dyd_file)
        # After the last dynModels so the generated connectors are applied last.
        existing = find_all(self._root, "dynModels")
        if existing:
            existing[-1].addnext(element)
        else:
            modeler.append(element)
        return True

    def ensure_interactive_settings(self, period: float | str) -> bool:
        """
        Add the real-time <interactiveSettings> block unless it is already there,
        in which case only couplingTimeStep is brought in line. Returns whether
        the document changed.
        """
        period = str(period)
        existing = find_one(self._root, "interactiveSettings")
        if existing is not None:
            if existing.attrib.get("couplingTimeStep") == period:
                return False
            existing.attrib["couplingTimeStep"] = period
            return True

        job = find_one(self._root, "job")
        if job is None:
            raise ValueError(f"{self.path.name} has no <job> element")

        settings = self._make("interactiveSettings", couplingTimeStep=period)

        channels = self._make("channels")
        channels.append(self._make("channel", id="zmq_input", kind="INPUT", type="ZMQ",
                                   endpoint=ZMQ_INPUT_ENDPOINT))
        channels.append(self._make("channel", id="zmq_output", kind="OUTPUT", type="ZMQ",
                                   endpoint=ZMQ_OUTPUT_ENDPOINT))
        settings.append(channels)

        streams = self._make("streams")
        for data, fmt in STREAMS:
            attrib = {"data": data, "channel": "zmq_output"}
            if fmt is not None:
                attrib["format"] = fmt
            streams.append(self._make("stream", **attrib))
        settings.append(streams)

        settings.append(self._make("clock", type="EXTERNAL", triggerChannel="zmq_input"))

        job.append(settings)
        return True

    def save(self) -> None:
        ET.indent(self._tree, space="    ")
        self._tree.write(str(self.path), xml_declaration=True, encoding="UTF-8")
