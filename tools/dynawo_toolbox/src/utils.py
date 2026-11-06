"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import os
from pathlib import Path

DYNAWO_HOME = os.getenv("DYNAWO_HOME", "")
if DYNAWO_HOME == "":
    JOBS_XSD_PATH = ""
    PAR_XSD_PATH = ""
    DYD_XSD_PATH = ""
    TL_XSD_PATH = ""
    DYNAWO_MYENVDYNAWO = ""
else:
    DYNAWO_HOME = Path(DYNAWO_HOME)
    JOBS_XSD_PATH = DYNAWO_HOME / "deploy/gcc11/shared/dynawo/share/xsd/jobs.xsd"
    PAR_XSD_PATH = DYNAWO_HOME / "deploy/gcc11/shared/dynawo/share/xsd/parameters.xsd"
    DYD_XSD_PATH = DYNAWO_HOME / "deploy/gcc11/shared/dynawo/share/xsd/dyd.xsd"
    TL_XSD_PATH = DYNAWO_HOME / "deploy/gcc11/shared/dynawo/share/xsd/timeline.xsd"
    DYNAWO_MYENVDYNAWO = f"{DYNAWO_HOME}/dynawo.sh"

DYNAWO_RTE_HOME = os.getenv("DYNAWO_RTE_HOME", "")
if DYNAWO_RTE_HOME == "":
    DYNAWO_MYENVDYNAWORTE = ""
else:
    DYNAWO_RTE_HOME = Path(DYNAWO_RTE_HOME)
    DYNAWO_MYENVDYNAWORTE = f"{DYNAWO_RTE_HOME}/dynawo.sh"

WORKSPACE_ROOT = Path(os.path.dirname(__file__)) / "../../workspace"
