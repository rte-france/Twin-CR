/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

// Generated from Orchestrator/DSL/PowerEventDSL.g4 by Orchestrator/DSL/tools/extract_keywords.py.
// Do not edit by hand: run the script instead.

#ifndef DSL_KEYWORDS_H
#define DSL_KEYWORDS_H

#include <array>
#include <string_view>

/** Reserved words of the DSL: every quoted literal in the grammar that is not an element type. */
inline constexpr std::array<std::string_view, 62> DSL_KEYWORDS = {{
    "after","and","at","by","change","characteristics","close","cluster","completed","corruption","decrease",
    "def","delay","drop","false","fixed","from","func","gauss","h","hour","hours","increase","input",
    "invert_control","is","law","likelihood","linear","link","mean","min","minute","minutes","network","node",
    "none","on","open","or","output","random","random_noise_control","random_noise_measurement","range",
    "regex","s","second","seconds","set","shift_measurement","stddev","tagged","to","transformer","true",
    "validate","value","when","when_rearming","with","zero_out_measurement"
}};

/** The gridElementType alternatives. Two of them start with a digit. */
inline constexpr std::array<std::string_view, 18> DSL_ELEMENT_TYPES = {{
    "2_windings_transformer","3_windings_transformer","battery","dangling_line","generator","hvdc_line",
    "lcc_converter_station","line","load","phase_tap_changer","ratio_tap_changer","shunt_compensator",
    "static_var_compensator","substation","switch","tie_line","voltage_level","vsc_converter_station"
}};

#endif // DSL_KEYWORDS_H
