/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { themeBalham } from "ag-grid-community";

export const agGridCustomTheme = themeBalham.withParams({
  backgroundColor: "var(--bg)",
  foregroundColor: "var(--fg)",
  textColor: "var(--fg)",
  headerBackgroundColor: "var(--table-header-bg)",
  oddRowBackgroundColor: "var(--table-alternate-bg)",
  rowHoverColor: "var(--theme-hover)",
  borderColor: "var(--table-border-color)",
  wrapperBorder: "var(--border)",
  borderRadius: 0,
  wrapperBorderRadius: 0,
  accentColor: "var(--links)",
  selectedRowBackgroundColor: "var(--sidebar-active-bg)",
  fontFamily: "var(--font)",
  fontSize: "12px",
});
