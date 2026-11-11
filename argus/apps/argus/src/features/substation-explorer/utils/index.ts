/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export const formatVoltage = (voltage: number) => {
  return `${voltage} kV`;
};

export const getVoltageLevelColor = (voltage: number) => {
  if (voltage >= 300 && voltage <= 500) return "sld-vl300to500";
  if (voltage >= 180 && voltage < 300) return "sld-vl180to300";
  if (voltage >= 120 && voltage < 180) return "sld-vl120to180";
  if (voltage >= 70 && voltage < 120) return "sld-vl70to120";
  if (voltage >= 50 && voltage < 70) return "sld-vl50to70";
  if (voltage >= 30 && voltage < 50) return "sld-vl30to50";
  if (voltage >= 0 && voltage < 30) return "sld-vl0to30";
  return "";
};
