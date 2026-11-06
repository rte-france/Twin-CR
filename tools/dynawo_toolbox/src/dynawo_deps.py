"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

"""
Resolution of the files a Dynawo jobs file pulls in.

A .jobs file names its solver/network/criteria/curves inputs and its dyd files,
and each dyd names the par files its models need. None of those have to appear
in a config.toml, so anything that ships a simulation has to walk the graph.
The same walk exists in C++ in Orchestrator/DynawoInterface/DynawoHandlers/
XmlHandler.cpp (JobHandler::getAllInputPaths); keep the two in step.
"""

from pathlib import Path

import lxml.etree as ET

DYN_NAMESPACE = {"dyn": "http://www.rte-france.com/dynawo"}

JOB_FILE_REFERENCES = (
    (".//dyn:solver", "parFile"),
    (".//dyn:network", "iidmFile"),
    (".//dyn:network", "parFile"),
    (".//dyn:dynModels", "dydFile"),
    (".//dyn:criteria", "criteriaFile"),
    (".//dyn:curves", "inputFile"),
)

DYD_FILE_REFERENCES = (
    (".//dyn:blackBoxModel", "parFile"),
)


def referenced_names(xml_file: str | Path, references) -> set[str]:
    """File names referenced by one XML file, as written in its attributes."""
    root = ET.parse(str(xml_file)).getroot()
    names = set()
    for element_path, attribute_name in references:
        for element in root.findall(element_path, DYN_NAMESPACE):
            value = element.attrib.get(attribute_name)
            if value:
                names.add(value)
    return names


def jobs_references(jobs_file: str | Path) -> set[str]:
    """Names a jobs file references directly, without following its dyd files."""
    return referenced_names(jobs_file, JOB_FILE_REFERENCES)


def dyd_references(dyd_file: str | Path) -> set[str]:
    """Par file names a dyd file references."""
    return referenced_names(dyd_file, DYD_FILE_REFERENCES)


def collect_dynawo_files(jobs_file: str | Path) -> set[Path]:
    """
    Every file the jobs file needs, resolved against its directory: the jobs file
    itself, what it references, and the par files named inside its dyd files.

    Referenced files that are absent are still returned, so callers can report
    precisely what is missing rather than failing on the first one.
    """
    jobs_file = Path(jobs_file)
    working_dir = jobs_file.parent
    paths = {jobs_file}

    dyd_files = set()
    for name in jobs_references(jobs_file):
        path = working_dir / name
        paths.add(path)
        if path.suffix == ".dyd":
            dyd_files.add(path)

    for dyd_file in dyd_files:
        if not dyd_file.is_file():
            continue  # reported as missing by the caller
        for name in dyd_references(dyd_file):
            paths.add(dyd_file.parent / name)

    return paths


def missing_dynawo_files(jobs_file: str | Path) -> set[Path]:
    """The subset of collect_dynawo_files that is not on disk."""
    return {path for path in collect_dynawo_files(jobs_file) if not path.is_file()}
