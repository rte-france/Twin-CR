"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Shared constants and mappings for the Power Event DSL engine.
"""

COMPONENT_MAP = {
    "load": "loads",
    "generator": "generators",
    "line": "lines",
    "switch": "switches",
    "bus": "buses",
    "busbarsection": "busbar_sections",
    "busbarSection": "busbar_sections",
    "battery": "batteries",
    "substation": "substations",
    "voltagelevel": "voltage_levels",
    "voltageLevel": "voltage_levels",
    "twowindingstransformer": "2_windings_transformers",
    "twoWindingsTransformer": "2_windings_transformers",
    "threewindingstransformer": "3_windings_transformers",
    "threeWindingsTransformer": "3_windings_transformers",
    "2_windings_transformer": "2_windings_transformers",
    "3_windings_transformer": "3_windings_transformers",
    "shunt": "shunt_compensators",
    "shunt_compensator": "shunt_compensators",
    "staticvarcompensator": "static_var_compensators",
    "staticVarCompensator": "static_var_compensators",
    "hvdcline": "hvdc_lines",
    "hvdcLine": "hvdc_lines",
}
