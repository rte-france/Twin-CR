/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

/**
 * An autocompletion answer, a suggestion is a full word (with quotes when relevant, e.g. input "P").
 * replace_from is the position of the start of the partial word to be replaced.
 */
export type DSLAutocompleteResponse = {
  suggestions: string[];
  replace_from: number;
};
