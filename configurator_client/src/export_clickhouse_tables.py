"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from enum import Enum

"""
List of clickhouse tables to export.
Notably we ignore all private tables (starting with "_") and InputFiles
"""
class Clickhouse_Tables(Enum):
    MeasurementSent = "MeasurementSent"
    ControlSent = "ControlSent"
    MeasurementReceived = "MeasurementReceived"
    ControlReceived = "ControlReceived"
    ActualMeasurement = "ActualMeasurement"
    Latest_ActualMeasurement = "Latest_ActualMeasurement"
    ActualControl = "ActualControl"
    TimeUpdate = "TimeUpdate"
    DynawoTimelineEvent = "DynawoTimelineEvent"
    DynawoConstraintEvent = "DynawoConstraintEvent"
    DumpStateEvent = "DumpStateEvent"
    RawDynawoCommand = "RawDynawoCommand"
    OutputFiles = "OutputFiles"
    GameMasterCommand = "GameMasterCommand"
    SCADACommand = "SCADACommand"
