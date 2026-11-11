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
import { ConstraintsService } from "./ConstraintsService";
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
    field: "eventType",
    headerName: "Type",
    width: 100,
    cellRenderer: (params: any) => {
      if (!params.value) return "";
      const isBegin = params.value === "BEGIN";
      const classes = isBegin
        ? "bg-[var(--warning-bg)] border-[var(--warning-border)] text-[var(--warning-icon)]"
        : "bg-[var(--code-bg)] border-[var(--pre-border)] text-[var(--code-text)]";
      return `<span class="text-[10px] font-bold px-1.5 py-0.5 rounded border ${classes}">${params.value}</span>`;
    },
  },
  {
    field: "modelName",
    headerName: "Model",
    width: 160,
    cellRenderer: (params: any) => {
      if (!params.value) return "";
      return `<span class="text-[10px] bg-[var(--code-bg)] text-[var(--code-text)] px-1.5 py-0.5 rounded border border-[var(--pre-border)]">${params.value}</span>`;
    },
  },
  {
    field: "description",
    headerName: "Description",
    flex: 1,
    wrapText: true,
    autoHeight: true,
    cellClass: "text-[var(--code-text)]",
  },
];

export const ConstraintsLog: Component = () => {
  return (
    <LogTable
      service={ConstraintsService}
      columnDefs={columnDefs}
      itemNameSingular="constraint"
      itemNamePlural="constraints"
      emptyMessage="No constraints"
      searchPlaceholder="Filter constraints..."
    />
  );
};
