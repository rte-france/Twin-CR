/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { For, Show, type Component } from "solid-js";
import { useSldContext } from "../providers/SldProvider";
import { useLineGoTo } from "../hooks/useLineGoto";
import { openInCentral } from "@/utils/openInCentral";
import { useEquipmentControl } from "../hooks/useEquipmentControl";
import { useActionPanelSelection } from "../hooks/useActionPanelSelection";
import { useProtectionEquipmentLabels } from "../hooks/useProtectionEquipmentLabels";
import { useLabelVisibility } from "../hooks/useLabelVisibility";
import { SldActionPanel } from "./SldActionPanel";
import { ProtectionEquipmentPopup } from "./ProtectionEquipmentPopup";
import { addNotification } from "@/features/notifications/store";
import { EquipmentSpinnerOverlay } from "./EquipmentSpinnerOverlay";

export const SldCanvas: Component = () => {
  const ctx = useSldContext();

  const { selectedItem, setSelectedItem } = useActionPanelSelection({
    svgRef: ctx.svgRef,
    metadata: () => ctx.sldData()?.sld?.metadata,
  });

  useLineGoTo({
    svgRef: ctx.svgRef,
    metadata: () => ctx.sldData()?.sld?.metadata,
    onGoToVoltageLevel: (nextVId) => {
      openInCentral({
        id: `vl - ${nextVId}`,
        title: `vl - ${nextVId}`,
        elementTag: "sld-viewer",
        params: {
          equipmentId: nextVId,
          type: "vl",
        },
      });
    },
  });

  const { pendingIds } = useEquipmentControl({
    svgRef: ctx.svgRef,
    metadata: () => ctx.sldData()?.sld?.metadata,
    requester: `operatorA`,
    onSuccess: (id, state) => addNotification({ message: `${id} is ${state}` }),
  });

  const { selected: selectedPe, setSelected: setSelectedPe } =
    useProtectionEquipmentLabels({
      svgRef: ctx.svgRef,
      metadata: () => ctx.sldData()?.sld?.metadata,
    });

  useLabelVisibility({
    svgRef: ctx.svgRef,
    metadata: () => ctx.sldData()?.sld?.metadata,
    showProtectionLabels: ctx.showProtectionLabels,
    showMeasurementLabels: ctx.showMeasurementLabels,
  });

  return (
    <>
      <SldActionPanel
        SelectedActionItem={selectedItem()}
        onClose={() => setSelectedItem(null)}
      />

      <Show when={selectedPe()}>
        <ProtectionEquipmentPopup
          open={!!selectedPe()}
          onClose={() => setSelectedPe(null)}
          data={selectedPe()}
          requester="operatorA"
        />
      </Show>

      <svg
        ref={ctx.setSvgRef}
        class="w-full h-full outline-none cursor-grab active:cursor-grabbing bg-bg"
        preserveAspectRatio="xMidYMid meet"
      >
        <g ref={ctx.setGRef}></g>
      </svg>

      <div class="absolute bottom-6 left-6 z-50 flex flex-col gap-2 pointer-events-none">
        <For each={Array.from(pendingIds())}>
          {(id) => (
            <EquipmentSpinnerOverlay id={id} label={`${id} toggling...`} />
          )}
        </For>
      </div>
    </>
  );
};
