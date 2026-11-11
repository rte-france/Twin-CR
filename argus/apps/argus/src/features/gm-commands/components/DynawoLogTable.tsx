/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Component } from "solid-js";
import type { ColDef } from "ag-grid-community";
import { LogTable } from "@/components/ui/LogTable";
import { GmCommandsService } from "./GmCommandsService";
import { formatTimeHHMMSS } from "@/utils/formatTimeHHMMSS";

const columnDefs: ColDef[] = [
  {
    headerName: "Time",
    valueGetter: (params) => params.data?.time,
    valueFormatter: (params) =>
      params.value != null ? formatTimeHHMMSS(params.value) : "",
    width: 110,
    cellClass: "text-inline-code-color whitespace-nowrap",
  },
  {
    headerName: "Simulated Time",
    valueGetter: (params) => params.data?.time,
    valueFormatter: (params) =>
      params.value != null ? Number(params.value).toFixed(4) : "",
    width: 140,
    cellClass: "text-inline-code-color whitespace-nowrap",
  },
  {
    field: "command_source",
    headerName: "Source",
    width: 130,
    cellRenderer: (params: any) => {
      if (!params.value) return "";
      return `<span class="text-[10px] bg-[var(--code-bg)] text-[var(--code-text)] px-1.5 py-0.5 rounded border border-[var(--pre-border)]">${params.value}</span>`;
    },
  },
  {
    field: "command",
    headerName: "Command Payload",
    flex: 1,
    wrapText: true,
    autoHeight: true,
    cellClass: "text-[var(--code-text)] font-mono",
  },
];

export const GmCommandsTable: Component = () => {
  return (
    <LogTable
      service={GmCommandsService}
      columnDefs={columnDefs}
      itemNameSingular="GM command"
      itemNamePlural="GM commands"
      emptyMessage="No commands"
      searchPlaceholder="Filter commands..."
    />
  );
};
