/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { Icon } from "@iconify-icon/solid";
import { TemplateRenamedResponse } from "@/services/session-manager/types";

export function TemplateTitle(props: {
  name: string;
  templateId: number;
  onRename: (templateId: number, newName: string) => Promise<TemplateRenamedResponse>;
}) {
  const [editing, setEditing] = createSignal(false);
  const [value, setValue] = createSignal(props.name);

  const save = async () => {
    const newName = value().trim();

    if (!newName) {
      setValue(props.name);
      setEditing(false);
      return;
    }

    if (newName !== props.name) {
      try{
        await props.onRename(props.templateId, newName);
      } catch(err) {
        console.error(err);
      }
      finally {
        setEditing(false);
      }
    }
  };

  const cancel = () => {
    setValue(props.name);
    setEditing(false);
  };

  return (
    <div class="flex items-center gap-2">
      {editing() ? (
        <input
          class="font-mono text-sm font-bold text-slate-800 px-2 py-1"
          value={value()}
          autofocus
          onInput={(e) => setValue(e.currentTarget.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") cancel();
          }}
        />
      ) : (
        <>
          <h2 class="font-mono text-sm font-bold text-slate-800 break-all">
            {props.name}
          </h2>

          <button
            class="text-slate-400 hover:text-slate-700"
            onClick={() => {
              setValue(props.name);
              setEditing(true);
            }}
            title="Rename"
          >
            <Icon icon="lucide:pencil"/>
          </button>
        </>
      )}
    </div>
  );
}
