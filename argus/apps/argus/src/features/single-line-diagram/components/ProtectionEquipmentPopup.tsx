/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, For, Show, createEffect, createMemo, createSignal } from "solid-js";
import { Dialog } from "@kobalte/core/dialog";
import { FiX } from "solid-icons/fi";
import { useAppMode } from "@/hooks/useAppMode";
import { Mode } from "@/services/app-mode";
import { backendPost } from "@/services/backend";
import { addNotification } from "@/features/notifications/store";
import type { SelectedProtectionEquipment } from "../hooks/useProtectionEquipmentLabels";

interface ProtectionEquipmentPopupProps {
  open: boolean;
  onClose: () => void;
  data: SelectedProtectionEquipment | null;
  requester: string;
}

const FIELD_LABELS: Record<string, string> = {
  libelle: "Libellé",
  tase2: "TASE2",
  tase2_control: "TASE2 control",
  value: "Value",
};

const FIELD_ORDER = ["libelle", "tase2", "tase2_control"];

// Su X protection equipments cannot be edited
const NON_EDITABLE_LABELS = ["Su 1", "Su 5", "Su 10", "Su 20", "Su 60"];

export const ProtectionEquipmentPopup: Component<ProtectionEquipmentPopupProps> = (
  props,
) => {
  const [mode] = useAppMode();
  const [editValue, setEditValue] = createSignal("");
  const [sending, setSending] = createSignal(false);

  createEffect(() => {
    setEditValue(props.data?.metadata.value ?? "");
  });

  const rows = () => {
    const metadata = props.data?.metadata;
    if (!metadata) return [];

    const keys = [
      ...FIELD_ORDER.filter((key) => key in metadata),
      ...Object.keys(metadata).filter(
        (key) => key !== "value" && !FIELD_ORDER.includes(key),
      ),
    ];

    return keys.map((key) => {
      const value = metadata[key];
      return {
        field: FIELD_LABELS[key] ?? key,
        value: value === null || value === undefined ? "—" : String(value),
      };
    });
  };

  // Raw id expected by the /control-raw endpoint — libelle in both modes
  const controlId = createMemo((): string | null => {
    return props.data?.metadata.libelle ?? null;
  });

  const isEditable = createMemo(() => {
    if (!props.data || !controlId()) return false;
    if (mode() === Mode.GameMaster) {
      return !NON_EDITABLE_LABELS.includes(props.data.label);
    }
    if (mode() === Mode.Scada) {
      return props.data.metadata.tase2_control != null;
    }
    return false;
  });

  const handleUpdate = async () => {
    const id = controlId();
    if (!id) return;

    setSending(true);
    try {
      await backendPost(
        `/control-raw/${encodeURIComponent(id)}/${encodeURIComponent(editValue())}?requester=${encodeURIComponent(props.requester)}`,
        {},
      );
      addNotification({ message: `${props.data?.metadata.libelle ?? id} updated to ${editValue()}` });
    } catch (e) {
      addNotification({
        message: `Failed to update ${id}: ${e instanceof Error ? e.message : String(e)}`,
        type: "error",
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog
      open={props.open}
      onOpenChange={(o) => {
        if (!o) props.onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
          <Dialog.Content class="pointer-events-auto w-full max-w-sm rounded-lg bg-[var(--popover-bg)] text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none">
            <div class="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
              <Dialog.Title class="text-sm font-medium text-[var(--title-color)]">
                Protection equipment
              </Dialog.Title>
              <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                <FiX class="size-4" />
              </Dialog.CloseButton>
            </div>

            <table class="w-full text-sm">
              <tbody>
                <For each={rows()}>
                  {(row) => (
                    <tr class="border-b border-[var(--divider)] last:border-0">
                      <td class="px-4 py-2 text-xs opacity-70 align-top whitespace-nowrap">
                        {row.field}
                      </td>
                      <td class="px-4 py-2 font-mono text-xs break-all">
                        {row.value}
                      </td>
                    </tr>
                  )}
                </For>
                <Show when={props.data}>
                  <tr class="border-b border-[var(--divider)] last:border-0">
                    <td class="px-4 py-2 text-xs opacity-70 align-top whitespace-nowrap">
                      {FIELD_LABELS.value}
                    </td>
                    <td class="px-4 py-2 font-mono text-xs">
                      <Show
                        when={isEditable()}
                        fallback={props.data?.metadata.value ?? "—"}
                      >
                        <div class="flex items-center gap-2">
                          <input
                            type="text"
                            value={editValue()}
                            onInput={(e) => setEditValue(e.currentTarget.value)}
                            disabled={sending()}
                            class="w-20 px-1.5 py-0.5 text-xs font-mono bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded focus:outline-none focus:border-[var(--links)] text-[var(--fg)] disabled:opacity-50"
                          />
                          <button
                            onClick={handleUpdate}
                            disabled={sending()}
                            class="px-2 py-1 text-xs rounded bg-[var(--links)] text-white hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {sending() ? "Updating…" : "Update"}
                          </button>
                        </div>
                      </Show>
                    </td>
                  </tr>
                </Show>
                <Show when={rows().length === 0 && !props.data}>
                  <tr>
                    <td
                      class="px-4 py-3 text-xs opacity-50 italic text-center"
                      colspan={2}
                    >
                      No data
                    </td>
                  </tr>
                </Show>
              </tbody>
            </table>
          </Dialog.Content>
        </div>
      </Dialog.Portal>
    </Dialog>
  );
};
