/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type ParentComponent, Show } from "solid-js";
import { Navigate } from "@solidjs/router";

import { useAuth } from "../hooks/useAuth";

interface RoleGuardProps {
  role: string;
  fallback?: string;
}

export const RoleGuard: ParentComponent<RoleGuardProps> = (props) => {
  const { hasRole } = useAuth();

  return (
    <Show
      when={hasRole(props.role)}
      fallback={
        props.fallback
          ? <Navigate href={props.fallback} />
          : <div class="p-8 text-center text-red-600 font-bold font-sans">Access Denied: Requires '{props.role}' role.</div>
      }
    >
      {props.children}
    </Show>
  );
};
