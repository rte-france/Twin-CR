/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface SettingFieldDefinition {
  key: string;
  label: string;
  description: string;
  type: "boolean" | "string" | "number" | "string[]" | "select";
  options?: { label: string; value: string }[];
  defaultValue?: any;
  placeholder?: string;
}

export interface SettingSectionDefinition {
  id: string;
  title: string;
  description?: string;
  fields: SettingFieldDefinition[];
}
